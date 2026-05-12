from app import create_app
from app.extensions import db
from app.models import User, Category, Product, Table, StoreSetting, UserRole, GenericStatus
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    print("Iniciando la inyección de datos semilla (COF-24)...")

    # 1. Crear 2 Usuarios (Admin y Cajero)
    admin_user = User(
        username="admin",
        password_hash=generate_password_hash("admin123"),
        role=UserRole.ADMIN
    )
    cashier_user = User(
        username="cashier",
        password_hash=generate_password_hash("cashier123"),
        role=UserRole.CASHIER
    )
    db.session.add_all([admin_user, cashier_user])

    # 2. Crear 5 Categorías
    cat_names = ["Café", "Bebidas Frías", "Postres", "Snacks", "Otros"]
    categories = []
    for i, name in enumerate(cat_names):
        cat = Category(name=name, slug=f"cat_{i}")
        categories.append(cat)
    db.session.add_all(categories)
    db.session.flush() # Flush para obtener los IDs temporalmente

    # 3. Crear 15 Productos distribuidos
    products = [
        Product(name="Espresso", sku="CAFE-001", price=3500, category_id=categories[0].id),
        Product(name="Americano", sku="CAFE-002", price=4000, category_id=categories[0].id),
        Product(name="Capuccino", sku="CAFE-003", price=5500, category_id=categories[0].id),
        Product(name="Latte", sku="CAFE-004", price=6000, category_id=categories[0].id),
        
        Product(name="Frappé de Caramelo", sku="FRIO-001", price=8000, category_id=categories[1].id),
        Product(name="Limonada Cerezada", sku="FRIO-002", price=6500, category_id=categories[1].id),
        Product(name="Té Helado", sku="FRIO-003", price=5000, category_id=categories[1].id),
        
        Product(name="Torta de Chocolate", sku="POST-001", price=7500, category_id=categories[2].id),
        Product(name="Cheesecake", sku="POST-002", price=8500, category_id=categories[2].id),
        Product(name="Brownie con Helado", sku="POST-003", price=9000, category_id=categories[2].id),
        
        Product(name="Empanada", sku="SNK-001", price=2500, category_id=categories[3].id),
        Product(name="Palito de Queso", sku="SNK-002", price=3000, category_id=categories[3].id),
        Product(name="Sandwich Jamón y Queso", sku="SNK-003", price=6000, category_id=categories[3].id),
        
        Product(name="Botella de Agua", sku="OTR-001", price=2500, category_id=categories[4].id),
        Product(name="Gaseosa", sku="OTR-002", price=3500, category_id=categories[4].id),
    ]
    db.session.add_all(products)

    # 4. Crear 8 Mesas
    tables = []
    for i in range(1, 9):
        # Capacidad aleatoria de 2 o 4 personas
        capacity = 4 if i % 2 == 0 else 2 
        tables.append(Table(name=f"Mesa {i}", capacity=capacity, status=GenericStatus.ACTIVE))
    db.session.add_all(tables)

    # 5. Crear 1 StoreSetting
    settings = StoreSetting(
        business_name="CoffeePOS Tienda Principal",
        tax_percentage=19.00,  # 19% IVA (por ejemplo)
        currency="COP",
        address="Centro, Neiva",
        phone="3000000000"
    )
    db.session.add(settings)

    try:
        db.session.commit()
        print("¡COF-24 Completado! Base de datos poblada con los criterios exactos de Jira.")
    except Exception as e:
        db.session.rollback()
        print(f"Error al poblar la base de datos: {e}")