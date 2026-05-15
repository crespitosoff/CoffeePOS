"""
seed.py — Inyección de datos iniciales
Basado en domain.py. Solo inserta productos ACTIVE del catálogo.
Seguro para re-ejecución: aborta si ya existen usuarios en la BD.
"""

from app import create_app
from app.extensions import db
from app.models.domain import (
    User, Category, Product, Table, StoreSetting,
    UserRole, UserStatus, GenericStatus,
)
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # ── Guard de idempotencia ────────────────────────────────────────────────
    if User.query.first():
        print("[SEED] Ya existen datos en la BD. Abortando para evitar duplicados.")
        exit(0)

    print("[SEED] Iniciando inyección de datos...")

    # ── 1. Usuarios ──────────────────────────────────────────────────────────
    users = [
        User(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            role=UserRole.ADMIN,
            first_name="Admin",
            last_name="Principal",
            email="admin@coffeepos.co",
            phone="3001234567",
            status=UserStatus.ACTIVE,
        ),
        User(
            username="cashier",
            password_hash=generate_password_hash("cashier123"),
            role=UserRole.CASHIER,
            first_name="Cajero",
            last_name="Principal",
            email="cajero@coffeepos.co",
            phone="3007654321",
            status=UserStatus.ACTIVE,
        ),
    ]
    db.session.add_all(users)
    print(f"  → {len(users)} usuarios creados.")

    # ── 2. Categorías ────────────────────────────────────────────────────────
    cat_data = [
        ("Café",          "cafe"),
        ("Bebidas Frías", "bebidas-frias"),
        ("Postres",       "postres"),
        ("Snacks",        "snacks"),
        ("Otros",         "otros"),
    ]
    categories: dict[str, Category] = {}
    for name, slug in cat_data:
        cat = Category(name=name, slug=slug, status=GenericStatus.ACTIVE)
        db.session.add(cat)
        categories[name] = cat

    db.session.flush()  # Obtiene los UUIDs antes del commit
    print(f"  → {len(categories)} categorías creadas.")

    # ── 3. Productos (solo registros 'active' del CSV) ───────────────────────
    #
    # Columnas: name, sku, price, unit_cost, stock, min_stock, image_url, category
    #
    # NOTA: El image_url del Americano (CAF-002) en el CSV apunta a la imagen
    # de la Torta de Chocolate. Es un error en el origen; se conserva tal cual.
    #
    products_data = [
        # ── Café ──────────────────────────────────────────────────────────────
        (
            "Espresso", "CAF-001", 3500, 2450, 12, 0,
            "https://res.cloudinary.com/dxfh4t8jw/image/upload/v1762061315/26_koaxec.jpg",
            "Café",
        ),
        (
            "Americano", "CAF-002", 4000, 2800, 33, 0,
            # ⚠ URL apunta a imagen de Torta de Chocolate — corregir en producción
            "https://media.istockphoto.com/id/1326149453/es/foto/rebanada-de-pastel-de-chocolate-negro.jpg"
            "?s=612x612&w=0&k=20&c=7nDwRIY7jFBTWw_4BbP00JoZcDMkVqoGejTOwG9e77o=",
            "Café",
        ),
        (
            "Capuccino", "CAF-003", 5500, 3850, 20, 3,
            "https://res.cloudinary.com/dxfh4t8jw/image/upload/v1762061659/"
            "WhatsApp_Image_2025-10-25_at_4.52.56_PM_2_cyv7ax.jpg",
            "Café",
        ),
        (
            "Latte", "CAF-004", 6000, 4200, 28, 0,
            "https://res.cloudinary.com/dxfh4t8jw/image/upload/v1762061327/66.1_lma2ds.jpg",
            "Café",
        ),
        # ── Bebidas Frías ─────────────────────────────────────────────────────
        (
            "Frappé de Caramelo", "FRI-001", 8000, 5600, 75, 0,
            "https://res.cloudinary.com/dxfh4t8jw/image/upload/v1762061325/"
            "WhatsApp_Image_2025-10-08_at_1.42.35_PM_yan0ii.jpg",
            "Bebidas Frías",
        ),
        (
            "Limonada Cerezada", "FRI-002", 6500, 4550, 37, 0,
            "https://res.cloudinary.com/dxfh4t8jw/image/upload/v1762061319/55.1_a9pf71.jpg",
            "Bebidas Frías",
        ),
        (
            "Té Helado", "FRI-003", 5000, 3500, 24, 0,
            "https://res.cloudinary.com/dxfh4t8jw/image/upload/v1762061333/"
            "WhatsApp_Image_2025-10-08_at_2.11.26_PM_tioi2j.jpg",
            "Bebidas Frías",
        ),
        # ── Postres ───────────────────────────────────────────────────────────
        (
            "Torta de Chocolate", "POT-001", 7500, 5250, 57, 0,
            "https://media.istockphoto.com/id/1326149453/es/foto/rebanada-de-pastel-de-chocolate-negro.jpg"
            "?s=612x612&w=0&k=20&c=7nDwRIY7jFBTWw_4BbP00JoZcDMkVqoGejTOwG9e77o=",
            "Postres",
        ),
        (
            "Cheesecake", "POT-002", 8500, 5950, 32, 0,
            "https://res.cloudinary.com/dxfh4t8jw/image/upload/v1762061149/samples/food/dessert.jpg",
            "Postres",
        ),
        (
            "Brownie con Helado", "POT-003", 9000, 6300, 18, 0,
            "https://res.cloudinary.com/dxfh4t8jw/image/upload/v1778613351/b-helado_dvxe6j.jpg",
            "Postres",
        ),
        # ── Snacks ────────────────────────────────────────────────────────────
        (
            "Empanada", "SNK-001", 2500, 1750, 15, 0,
            "https://therecipecritic.com/wp-content/uploads/2025/08/empanadas.jpg",
            "Snacks",
        ),
        (
            "Palito de Queso", "SNK-002", 3000, 2100, 22, 0,
            "https://elmolino.com.co/wp-content/uploads/2020/05/palitos-de-queso-artesanales-el-molino-cali.webp",
            "Snacks",
        ),
        (
            "Sandwich Jamón y Queso", "SNK-003", 6000, 4200, 26, 0,
            "https://img.freepik.com/fotos-premium/sandwich-jamon-queso_105495-191.jpg",
            "Snacks",
        ),
        # ── Otros ─────────────────────────────────────────────────────────────
        (
            "Botella de Agua", "OTR-001", 2500, 1750, 20, 0,
            "https://http2.mlstatic.com/D_NQ_NP_925362-MLM94592678424_102025-O.webp",
            "Otros",
        ),
        (
            "Gaseosa", "OTR-002", 3500, 2450, 37, 0,
            "https://img.magnific.com/fotos-premium/botella-coca-cola-muestra-etiqueta-roja_854579-298.jpg"
            "?semt=ais_hybrid&w=740&q=80",
            "Otros",
        ),
    ]

    for name, sku, price, unit_cost, stock, min_stock, image_url, cat_key in products_data:
        db.session.add(Product(
            name=name,
            sku=sku,
            price=price,
            unit_cost=unit_cost,
            stock=stock,
            min_stock=min_stock,
            image_url=image_url,
            category_id=categories[cat_key].id,
            status=GenericStatus.ACTIVE,
        ))

    print(f"  → {len(products_data)} productos creados.")

    # ── 4. Mesas ─────────────────────────────────────────────────────────────
    tables = [
        Table(
            name=f"Mesa {i}",
            capacity=4 if i % 2 == 0 else 2,
            status=GenericStatus.ACTIVE,
        )
        for i in range(1, 9)
    ]
    db.session.add_all(tables)
    print(f"  → {len(tables)} mesas creadas.")

    # ── 5. StoreSetting ──────────────────────────────────────────────────────
    db.session.add(StoreSetting(
        business_name="Tiendas de Promisión",
        commercial_name="CoffeePOS",
        address="Centro, Neiva, Huila",
        phone="3000000000",
        email="info@coffeepos.co",
        currency="COP",
        language="es-CO",
        timezone="America/Bogota",
        country_code="CO",
        tax_percentage=19.00,
        invoice_prefix="FAC",
        next_invoice_number=1,
        receipt_footer="¡Gracias por tu visita! Vuelve pronto.",
    ))
    print("  → StoreSetting creado.")

    # ── Commit ───────────────────────────────────────────────────────────────
    try:
        db.session.commit()
        print("[SEED] Completado exitosamente.")
    except Exception as e:
        db.session.rollback()
        print(f"[SEED] Error durante el commit: {e}")
        raise