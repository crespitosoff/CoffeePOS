from flask import Blueprint, jsonify
from app.services.product_service import ProductService

pos_bp = Blueprint('pos', __name__)

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