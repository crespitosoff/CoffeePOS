import os
from flask import Flask
from app.extensions import db
from dotenv import load_dotenv

def create_app():
    load_dotenv()
    
    app = Flask(__name__)
    
    # Configuración base
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializar extensiones
    db.init_app(app)

    # Registrar Blueprints (Rutas)
    from app.routes.pos import pos_bp
    app.register_blueprint(pos_bp, url_prefix='/api/pos')

    return app