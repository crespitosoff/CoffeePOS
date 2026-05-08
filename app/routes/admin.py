from flask import Blueprint, render_template_string
from flask_login import login_required
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Usamos render_template_string para una prueba rápida sin crear archivos HTML extra aún
    return render_template_string("""
        <h1>Dashboard de Administrador</h1>
        <p>Si ves esto, tienes privilegios de nivel 1.</p>
        <a href="/logout">Cerrar Sesión</a>
    """)