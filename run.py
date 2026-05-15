from app import create_app
from app.extensions import db
from app.models.domain import (
    User,
    UserRole,
    UserStatus,
)
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    db.create_all()
    print("Tablas verificadas/creadas en la base de datos.")
    admin_exists = User.query.filter_by(username="admin").first()
    if not admin_exists:
        admin_user = User(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            role=UserRole.ADMIN,
            first_name="Admin",
            last_name="Principal",
            status=UserStatus.ACTIVE,
        )
        db.session.add(admin_user)
        db.session.commit()
        print("¡Usuario administrador creado exitosamente!")
if __name__ == "__main__":
    app.run(debug=True, port=5000)
