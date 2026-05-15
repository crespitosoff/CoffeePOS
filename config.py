import os
from dotenv import load_dotenv

load_dotenv() # Carga el .env para que os.getenv funcione

class Config:
    # Obtiene las variables del .env, o usa valores por defecto si no existen
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')