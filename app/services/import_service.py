# app/services/import_service.py  –  COF-39 (v3)
# Importación masiva con Upsert por SKU y auto-creación de categorías
from __future__ import annotations

import csv
import io
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.domain import Category, GenericStatus, Product


class ImportService:
    """
    Lee un CSV de productos y los importa masivamente con lógica UPSERT.

    Columnas del CSV (en español — compatible con la plantilla de descarga):
        sku          – identificador único obligatorio
        nombre       – nombre del producto (str, no vacío)
        categoria    – nombre de categoría; se crea automáticamente si no existe
        precio       – precio de venta (Decimal >= 0)
        stock        – stock inicial (int >= 0)
        descripcion  – descripción larga (str, opcional)
        image_url    – URL de imagen (str, opcional)

    También acepta cabeceras en inglés: name, category, price, description.

    Lógica UPSERT:
        - Si el SKU ya existe → actualiza nombre, precio, stock, descripción,
          imagen y categoría del producto existente.
        - Si el SKU no existe → crea un producto nuevo.
        - Nunca duplica productos por SKU.

    Retorna:
        {
            'imported':  int,   # productos creados
            'updated':   int,   # productos actualizados
            'skipped':   int,   # filas rechazadas por errores fatales
            'errors':    list[dict],
        }
    """

    REQUIRED_COLUMNS = {"sku", "nombre", "precio", "stock", "categoria", "precio_costo", "stock_minimo", "status"}

    # Alias inglés → español interno
    COLUMN_ALIASES: dict[str, str] = {
        "name":        "nombre",
        "category":    "categoria",
        "price":       "precio",
        "description": "descripcion",
        "unit_cost":   "precio_costo",
        "min_stock":   "stock_minimo",
    }

    # -------------------------------------------------------------------------
    # Punto de entrada público
    # -------------------------------------------------------------------------

    @staticmethod
    def process_csv(file_stream) -> dict:
        """Procesa el CSV y realiza el upsert completo."""

        # ── 1. Leer bytes y decodificar (eliminar BOM de Excel) ──────────
        try:
            raw = file_stream.read() if hasattr(file_stream, "read") else file_stream
            if isinstance(raw, bytes):
                raw = raw.lstrip(b"\xef\xbb\xbf").decode("utf-8", errors="replace")
        except Exception as exc:
            raise ValueError(f"No se pudo leer el archivo: {exc}") from exc

        # ── 2. Parsear CSV ────────────────────────────────────────────────
        try:
            reader = csv.DictReader(io.StringIO(raw))
            if reader.fieldnames is None:
                raise ValueError("El archivo está vacío o no tiene encabezados.")
        except Exception as exc:
            raise ValueError(f"No se pudo parsear el CSV: {exc}") from exc

        # ── 3. Normalizar cabeceras (strip + lower + alias) ───────────────
        raw_fields = [f.strip().lower() for f in reader.fieldnames if f]
        norm_fields = [
            ImportService.COLUMN_ALIASES.get(f, f) for f in raw_fields
        ]
        field_map = dict(zip(raw_fields, norm_fields))

        missing = ImportService.REQUIRED_COLUMNS - set(norm_fields)
        if missing:
            raise ValueError(
                f"El CSV no contiene las columnas requeridas: {', '.join(sorted(missing))}. "
                f"Columnas encontradas: {', '.join(raw_fields)}"
            )

        # ── 4. Caché de categorías (nombre_lower → Category) ─────────────
        category_cache: dict[str, Category] = {
            c.name.strip().lower(): c
            for c in db.session.query(Category)
            .filter(Category.status == GenericStatus.ACTIVE)
            .all()
        }

        # ── 5. Caché de SKUs existentes ───────────────────────────────────
        sku_cache: dict[str, Product] = {
            p.sku: p
            for p in db.session.query(Product).filter(Product.sku.isnot(None)).all()
        }

        # ── 6. Procesar fila a fila ───────────────────────────────────────
        to_insert: list[Product] = []
        to_update: list[Product] = []
        errors: list[dict]       = []

        for row_num, raw_row in enumerate(reader, start=2):
            row = {
                field_map.get(k.strip().lower(), k.strip().lower()): (v.strip() if v else "")
                for k, v in raw_row.items()
                if k is not None
            }

            error = ImportService._validate_row(row_num, row)
            if error:
                errors.append(error)
                continue

            # Campos obligatorios
            sku   = row["sku"].strip()
            name  = row["nombre"].strip()
            price = Decimal(str(row["precio"]))
            stock = int(float(row["stock"]))
            unit_cost = Decimal(str(row["precio_costo"]))
            min_stock = int(float(row["stock_minimo"]))
            
            status_str = row["status"].strip().lower()
            status_enum = GenericStatus.ACTIVE
            if status_str == "archived":
                status_enum = GenericStatus.ARCHIVED
            elif status_str == "inactive":
                status_enum = GenericStatus.INACTIVE

            # Campos opcionales
            description = row.get("descripcion", "").strip() or None
            image_url   = row.get("image_url",   "").strip() or None

            # Resolver / crear categoría
            category_id: Optional[str] = None
            raw_cat = row["categoria"].strip()
            if raw_cat:
                cat_key = raw_cat.lower()
                cat_obj = category_cache.get(cat_key)
                if not cat_obj:
                    # Crear categoría al vuelo
                    cat_obj = Category(
                        name=raw_cat,
                        slug=ImportService._slugify(raw_cat),
                        status=GenericStatus.ACTIVE,
                    )
                    db.session.add(cat_obj)
                    try:
                        db.session.flush()   # obtener el UUID generado
                        category_cache[cat_key] = cat_obj
                    except SQLAlchemyError as exc:
                        db.session.rollback()
                        errors.append({
                            "row":    row_num,
                            "field":  "categoria",
                            "value":  raw_cat,
                            "reason": f"No se pudo crear la categoría '{raw_cat}': {str(exc)[:120]}",
                        })
                        continue
                category_id = str(cat_obj.id)

            # ── UPSERT ────────────────────────────────────────────────────
            existing = sku_cache.get(sku)
            if existing:
                existing.name        = name
                existing.price       = price
                existing.stock       = stock
                existing.description = description
                if image_url:
                    existing.image_url = image_url
                existing.unit_cost   = unit_cost
                existing.min_stock   = min_stock
                existing.status      = status_enum
                if category_id:
                    existing.category_id = category_id
                to_update.append(existing)
            else:
                product = Product(
                    name=name,
                    sku=sku,
                    price=price,
                    stock=stock,
                    description=description,
                    image_url=image_url,
                    unit_cost=unit_cost,
                    min_stock=min_stock,
                    category_id=category_id,
                    status=status_enum,
                )
                to_insert.append(product)
                sku_cache[sku] = product   # evitar duplicados dentro del CSV

        # ── 7. Persistir ──────────────────────────────────────────────────
        fatal_errors = [e for e in errors if not e.get("warning")]
        imported = 0
        updated  = 0

        if to_insert:
            try:
                db.session.add_all(to_insert)
                db.session.commit()
                imported = len(to_insert)
            except SQLAlchemyError:
                db.session.rollback()
                i, errors = ImportService._insert_one_by_one(to_insert, errors)
                imported = i

        if to_update:
            try:
                db.session.commit()
                updated = len(to_update)
            except SQLAlchemyError:
                db.session.rollback()
                for p in to_update:
                    try:
                        db.session.commit()
                        updated += 1
                    except SQLAlchemyError as exc:
                        db.session.rollback()
                        errors.append({
                            "row":    "?",
                            "field":  "db",
                            "value":  p.sku,
                            "reason": f"Error al actualizar '{p.sku}': {str(exc)[:120]}",
                        })

        return {
            "imported": imported,
            "updated":  updated,
            "skipped":  len(fatal_errors),
            "errors":   errors,
        }

    # -------------------------------------------------------------------------
    # Descarga del catálogo actual como CSV
    # -------------------------------------------------------------------------

    @staticmethod
    def export_catalog_csv() -> bytes:
        """
        Exporta todos los productos activos como CSV con BOM UTF-8.
        Sirve como plantilla de edición masiva (ya tiene SKUs reales).
        """
        products = (
            db.session.query(Product)
            .filter(Product.status == GenericStatus.ACTIVE)
            .order_by(Product.name)
            .all()
        )

        buf = io.StringIO()
        writer = csv.writer(buf)

        # Cabeceras en español (idénticas a REQUIRED_COLUMNS del importador)
        writer.writerow(["sku", "nombre", "categoria", "precio", "stock",
                         "descripcion", "image_url", "precio_costo", "stock_minimo", "status"])

        for p in products:
            writer.writerow([
                p.sku or "",
                p.name,
                p.category.name if p.category else "",
                str(p.price),
                str(p.stock or 0),
                p.description or "",
                p.image_url or "",
                str(p.unit_cost or 0),
                str(p.min_stock or 0),
                p.status.value if p.status else "active",
            ])

        content = "\ufeff" + buf.getvalue()   # BOM para Excel
        return content.encode("utf-8")

    # -------------------------------------------------------------------------
    # Helpers privados
    # -------------------------------------------------------------------------

    @staticmethod
    def _validate_row(row_num: int, row: dict) -> Optional[dict]:
        sku = row.get("sku", "")
        if not sku:
            return {"row": row_num, "field": "sku",
                    "value": sku, "reason": "El SKU no puede estar vacío."}

        name = row.get("nombre", "")
        if not name:
            return {"row": row_num, "field": "nombre",
                    "value": name, "reason": "El nombre no puede estar vacío."}

        price = row.get("precio", "")
        try:
            p = Decimal(str(price))
            if p < Decimal("0"):
                raise ValueError
        except (InvalidOperation, ValueError, TypeError):
            return {"row": row_num, "field": "precio",
                    "value": price, "reason": f"Precio inválido: '{price}'."}

        stock = row.get("stock", "")
        try:
            s = int(float(str(stock)))
            if s < 0:
                raise ValueError
        except (ValueError, TypeError):
            return {"row": row_num, "field": "stock",
                    "value": stock, "reason": f"Stock inválido: '{stock}'."}
                    
        category = row.get("categoria", "")
        if not category:
            return {"row": row_num, "field": "categoria",
                    "value": category, "reason": "La categoría no puede estar vacía."}

        unit_cost = row.get("precio_costo", "")
        try:
            uc = Decimal(str(unit_cost))
            if uc < Decimal("0"):
                raise ValueError
        except (InvalidOperation, ValueError, TypeError):
            return {"row": row_num, "field": "precio_costo",
                    "value": unit_cost, "reason": f"Precio de costo inválido: '{unit_cost}'."}

        min_stock = row.get("stock_minimo", "")
        try:
            ms = int(float(str(min_stock)))
            if ms < 0:
                raise ValueError
        except (ValueError, TypeError):
            return {"row": row_num, "field": "stock_minimo",
                    "value": min_stock, "reason": f"Stock mínimo inválido: '{min_stock}'."}
                    
        status = row.get("status", "").strip().lower()
        if status not in ["active", "inactive", "archived"]:
            return {"row": row_num, "field": "status",
                    "value": status, "reason": f"Estado inválido: '{status}'. Debe ser active, inactive, o archived."}

        return None

    @staticmethod
    def _slugify(text: str) -> str:
        """Genera un slug URL-amigable a partir de un string."""
        text = text.lower().strip()
        text = re.sub(r"[áàäâ]", "a", text)
        text = re.sub(r"[éèëê]", "e", text)
        text = re.sub(r"[íìïî]", "i", text)
        text = re.sub(r"[óòöô]", "o", text)
        text = re.sub(r"[úùüû]", "u", text)
        text = re.sub(r"ñ", "n", text)
        text = re.sub(r"[^a-z0-9]+", "-", text)
        text = text.strip("-")
        # Garantizar unicidad ligera con sufijo numérico si hay colisión
        return text[:110]

    @staticmethod
    def _safe_decimal(value, default: Decimal) -> Decimal:
        if not value:
            return default
        try:
            r = Decimal(str(value))
            return r if r >= Decimal("0") else default
        except (InvalidOperation, TypeError):
            return default

    @staticmethod
    def _safe_int(value, default: int) -> int:
        if not value:
            return default
        try:
            r = int(float(str(value)))
            return r if r >= 0 else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _insert_one_by_one(
        products: list[Product],
        existing_errors: list[dict],
    ) -> tuple[int, list[dict]]:
        imported = 0
        errors   = list(existing_errors)
        for p in products:
            try:
                db.session.add(p)
                db.session.commit()
                imported += 1
            except SQLAlchemyError as exc:
                db.session.rollback()
                errors.append({
                    "row": "?", "field": "db", "value": p.name,
                    "reason": f"Error al insertar '{p.name}': {str(exc)[:120]}",
                })
        return imported, errors
