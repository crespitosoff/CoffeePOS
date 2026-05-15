#!/usr/bin/env bash
# Salir si algún comando falla
set -o errexit

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar las migraciones de la base de datos (crear tablas)
flask db upgrade

# (Opcional) Si tienes tu seed.py para el usuario inicial, quita el comentario a la siguiente línea:
python seed.py