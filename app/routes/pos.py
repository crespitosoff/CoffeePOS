from flask import Blueprint, render_template_string, jsonify
from flask_login import login_required
from app.utils.decorators import cashier_required
from app.services.product_service import ProductService

pos_bp = Blueprint('pos', __name__, url_prefix='/pos')

@pos_bp.route('/dashboard')
@login_required
@cashier_required
def dashboard():
    # Usamos render_template_string para una prueba rápida sin crear archivos HTML extra aún
    return render_template_string("""
        <h1>Pantalla de Ventas (Caja)</h1>
        <p>Si ves esto, puedes procesar pedidos.</p>
        <a href="/logout">Cerrar Sesión</a>
    """)

@pos_bp.route('/menu', methods=['GET'])
def get_menu():
    try:
        # LLama al método get_full_menu() del ProductService para obtener el menú completo.
        menu = ProductService.get_full_menu()

        # Retorna el resultado envuelto en la función jsonify() con un código HTTP 200.
        return jsonify(menu), 200
        pass
    
    except Exception as e:
        # En caso de error, retorna un mensaje de error con un código HTTP 500.
        return jsonify({'error': str(e)}), 500