import os
from flask import Flask
from config import Config
from app.extensions import db, migrate

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)

    # Registrar Blueprints (Rutas)
    from app.routes.pos import pos_bp
    app.register_blueprint(pos_bp, url_prefix='/api/pos')

    return app