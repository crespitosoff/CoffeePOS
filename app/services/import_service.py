# app/services/import_service.py  –  COF-39
# Servicio de importación masiva de productos desde CSV
# Reescrito sin pandas (Python puro: csv.DictReader)
from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.domain import Category, GenericStatus, Product


class ImportService:
    """
    Lee un CSV de productos y los importa masivamente a la base de datos.

    Columnas requeridas en el CSV:
        name    – nombre del producto (str, no vacío)
        price   – precio de venta (Decimal >= 0)
        stock   – stock inicial (int >= 0)

    Columnas opcionales:
        category    – nombre de categoría (str) – se busca por nombre exacto
        sku         – código único (str)
        description – descripción larga (str)
        unit_cost   – costo unitario (Decimal >= 0)
        min_stock   – stock mínimo de alerta (int >= 0)

    El método process_csv() retorna:
        {
            'imported': int,           # productos insertados correctamente
            'skipped':  int,           # filas ignoradas por errores fatales
            'errors':   list[dict],    # detalle de cada fila con error/warning
        }

    Compatible con la plantilla de 5 columnas en español:
        nombre, categoria, precio, stock, descripcion
    """

    # Columnas en inglés (API original)
    REQUIRED_COLUMNS = {"name", "price", "stock"}

    # Alias español → inglés para la plantilla de descarga del admin
    COLUMN_ALIASES: dict[str, str] = {
        "nombre":      "name",
        "categoria":   "category",
        "precio":      "price",
        "descripcion": "description",
    }

    @staticmethod
    def process_csv(file_stream) -> dict:
        """
        Punto de entrada principal. Acepta un objeto tipo-fichero (werkzeug
        FileStorage o cualquier io.BytesIO / io.StringIO) y procesa el CSV.
        """
        # ── 1. Leer contenido como texto ─────────────────────────────────
        try:
            raw = file_stream.read() if hasattr(file_stream, "read") else file_stream
            if isinstance(raw, bytes):
                # Eliminar BOM UTF-8 si está presente (generado por Excel)
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

        # ── 3. Normalizar y traducir cabeceras ────────────────────────────
        # Normalizar: strip + lowercase
        original_fields = [f.strip().lower() for f in reader.fieldnames]
        # Aplicar alias (ej. "nombre" → "name")
        normalized_fields = [
            ImportService.COLUMN_ALIASES.get(f, f) for f in original_fields
        ]

        # Verificar columnas requeridas
        missing = ImportService.REQUIRED_COLUMNS - set(normalized_fields)
        if missing:
            raise ValueError(
                f"El CSV no contiene las columnas requeridas: {', '.join(sorted(missing))}. "
                f"Columnas encontradas: {', '.join(original_fields)}"
            )

        # Construir mapa original → normalizado para reescribir cada fila
        field_map = dict(zip(original_fields, normalized_fields))

        # ── 4. Construir caché de categorías (nombre → UUID) ─────────────
        categories = (
            db.session.query(Category)
            .filter(Category.status == GenericStatus.ACTIVE)
            .all()
        )
        category_map: dict[str, str] = {
            c.name.strip().lower(): str(c.id) for c in categories
        }

        # ── 5. Procesar fila a fila ───────────────────────────────────────
        products_to_insert: list[Product] = []
        errors: list[dict] = []

        for row_num, raw_row in enumerate(reader, start=2):
            # Renombrar claves de la fila usando el mapa de normalización
            row = {
                field_map.get(k.strip().lower(), k.strip().lower()): (v.strip() if v else "")
                for k, v in raw_row.items()
                if k is not None
            }

            # Validar campos requeridos
            error = ImportService._validate_row(row_num, row)
            if error:
                errors.append(error)
                continue

            # Parsear campos obligatorios
            name  = row["name"].strip()
            price = Decimal(str(row["price"]))
            stock = int(float(row["stock"]))

            # Parsear campos opcionales
            sku         = row.get("sku", "").strip() or None
            description = row.get("description", "").strip() or None
            unit_cost   = ImportService._safe_decimal(row.get("unit_cost"), Decimal("0"))
            min_stock   = ImportService._safe_int(row.get("min_stock"), 0)

            # Resolver categoría por nombre
            category_id: Optional[str] = None
            raw_category = row.get("category", "").strip()
            if raw_category:
                cat_key = raw_category.lower()
                category_id = category_map.get(cat_key)
                if not category_id:
                    errors.append({
                        "row":     row_num,
                        "field":   "category",
                        "value":   raw_category,
                        "reason":  f"Categoría '{raw_category}' no encontrada. Fila importada sin categoría.",
                        "warning": True,  # advertencia, no error fatal
                    })

            product = Product(
                name=name,
                price=price,
                stock=stock,
                sku=sku,
                description=description,
                unit_cost=unit_cost,
                min_stock=min_stock,
                category_id=category_id,
                status=GenericStatus.ACTIVE,
            )
            products_to_insert.append(product)

        # ── 6. Inserción masiva ───────────────────────────────────────────
        fatal_errors = [e for e in errors if not e.get("warning")]
        imported = 0

        if products_to_insert:
            try:
                db.session.add_all(products_to_insert)
                db.session.commit()
                imported = len(products_to_insert)
            except SQLAlchemyError:
                db.session.rollback()
                # Fallback: insertar uno a uno para aislar el producto que falla
                imported, errors = ImportService._insert_one_by_one(
                    products_to_insert, errors
                )

        skipped = len(fatal_errors)
        return {
            "imported": imported,
            "skipped":  skipped,
            "errors":   errors,
        }

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_row(row_num: int, row: dict) -> Optional[dict]:
        """
        Valida una fila del CSV. Retorna un dict de error si la fila es
        inválida, o None si es correcta.
        """
        name = row.get("name", "")
        if not name or str(name).strip() == "":
            return {
                "row":    row_num,
                "field":  "name",
                "value":  name,
                "reason": "El nombre del producto no puede estar vacío.",
            }

        price = row.get("price", "")
        try:
            price_dec = Decimal(str(price))
            if price_dec < Decimal("0"):
                raise ValueError("negativo")
        except (InvalidOperation, ValueError, TypeError):
            return {
                "row":    row_num,
                "field":  "price",
                "value":  price,
                "reason": f"Precio inválido o negativo: '{price}'.",
            }

        stock = row.get("stock", "")
        try:
            stock_int = int(float(str(stock)))
            if stock_int < 0:
                raise ValueError("negativo")
        except (ValueError, TypeError):
            return {
                "row":    row_num,
                "field":  "stock",
                "value":  stock,
                "reason": f"Stock inválido o negativo: '{stock}'.",
            }

        return None  # fila válida

    @staticmethod
    def _safe_decimal(value, default: Decimal) -> Decimal:
        """Convierte un valor a Decimal de forma segura."""
        if not value:
            return default
        try:
            result = Decimal(str(value))
            return result if result >= Decimal("0") else default
        except (InvalidOperation, TypeError):
            return default

    @staticmethod
    def _safe_int(value, default: int) -> int:
        """Convierte un valor a int de forma segura."""
        if not value:
            return default
        try:
            result = int(float(str(value)))
            return result if result >= 0 else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _insert_one_by_one(
        products: list[Product],
        existing_errors: list[dict],
    ) -> tuple[int, list[dict]]:
        """
        Fallback: inserta productos uno a uno cuando el add_all masivo falla.
        Identifica cuáles productos individualmente causan errores.
        """
        imported = 0
        errors   = list(existing_errors)

        for product in products:
            try:
                db.session.add(product)
                db.session.commit()
                imported += 1
            except SQLAlchemyError as exc:
                db.session.rollback()
                errors.append({
                    "row":    "?",
                    "field":  "db",
                    "value":  product.name,
                    "reason": f"Error al insertar '{product.name}': {str(exc)[:120]}",
                })

        return imported, errors
