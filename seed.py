from app import create_app
from app.extensions import db
from app.models import User, Category, Product, UserRole
from werkzeug.security import generate_password_hash
from sqlalchemy import text

app = create_app()

with app.app_context():
    
    # 1. Tu idea de Probar Conexión primero
    try:
        db.session.execute(text('SELECT 1'))
        print("Conexión a la base de datos exitosa.")
    except Exception as e:
        print(f"Error fatal de conexión: {e}")
        exit()

    print("Iniciando la inyección de datos semilla...")

    # Opcional: Limpiar datos viejos sin destruir la estructura SQL
    # db.session.query(Product).delete()
    # db.session.query(Category).delete()
    # db.session.query(User).delete()

    # 2. Tu idea del Hash para la contraseña
    hashed_password = generate_password_hash("admin123")

    user_admin = User(
        username="admin",
        password_hash=hashed_password,
        role=UserRole.ADMIN,
        # Añade aquí first_name, last_name, etc., si son obligatorios en tu SQL
    )

    # 3. Diferenciar variables
    cat_frias = Category(name="Bebidas Frías", slug="beb_fri")
    cat_calientes = Category(name="Bebidas Calientes", slug="beb_cal")

    # 4. Magia de SQLAlchemy: En lugar de category_id=X, le pasas el objeto 'category=...'
    prod_1 = Product(name="Capuccino", sku="beb_cal_cap", category=cat_calientes, price=5000)
    prod_2 = Product(name="Malteada de Chocolate", sku="beb_fri_mal_cho", category=cat_frias, price=8000)
    prod_3 = Product(name="Granizado de Café", sku="beb_fri_gra_caf", category=cat_frias, price=6000)

    # 5. Agregar masivamente
    db.session.add(user_admin)
    db.session.add_all([cat_frias, cat_calientes])
    db.session.add_all([prod_1, prod_2, prod_3])

    try:
        db.session.commit()
        print("¡Base de datos poblada exitosamente! Ya tenemos munición.")
    except Exception as e:
        db.session.rollback()
        print(f"La base de datos rechazó los datos. Revisa tus NOT NULL: {e}")