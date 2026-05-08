import os
import uuid
from flask import Flask, render_template
from config import Config
from app.extensions import db, migrate
from flask_login import LoginManager

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)

    # Configuración de Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'  # Redirige a esta ruta si no está autenticado
    login_manager.init_app(app)

    # Cargar modelo de usuario
    from app.models.domain import User
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.query(User).get(uuid.UUID(user_id))
        except ValueError:
            return None

    # Registrar blueprints
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp)
    
    from app.routes.pos import pos_bp
    app.register_blueprint(pos_bp)

    from app.routes.cash import cash_bp
    app.register_blueprint(cash_bp)

    # Manejo de errores personalizados
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    return app