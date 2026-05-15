from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.cash_movement_service import CashMovementService
from app.utils.decorators import cashier_required

cash_bp = Blueprint('cash', __name__, url_prefix='/api/cash')


@cash_bp.route('/movement', methods=['POST'])
@login_required
@cashier_required
def register_movement():
    """
    Endpoint JSON para registrar retiros y depósitos manuales en caja.
    Solo acepta 'withdrawal' y 'deposit'; las ventas en efectivo se registran
    automáticamente desde PaymentService, no desde aquí.

    Body JSON esperado:
        session_id   (str)  – UUID de la sesión activa
        amount       (float) – monto positivo
        type         (str)  – 'withdrawal' | 'deposit'
        description  (str)  – motivo del movimiento (recomendado para auditoría)
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No se enviaron datos"}), 400

    session_id    = data.get('session_id')
    amount        = data.get('amount')
    movement_type = data.get('type')
    description   = data.get('description', '')

    if not all([session_id, amount, movement_type]):
        return jsonify({"error": "Faltan parámetros requeridos (session_id, amount, type)"}), 400

    try:
        # Convertir a float antes de pasar al servicio; CashMovementService
        # lo convierte internamente a Decimal para precisión monetaria.
        amount = float(amount)
        if movement_type == 'withdrawal':
            movement = CashMovementService.record_withdrawal(session_id, str(current_user.id), amount, description)
        elif movement_type == 'deposit':
            movement = CashMovementService.record_deposit(session_id, str(current_user.id), amount, description)
        else:
            return jsonify({"error": "Tipo de movimiento no soportado en este endpoint"}), 400

        return jsonify({
            "message": "Movimiento registrado exitosamente",
            "movement_id": str(movement.id),
            "balance_after": float(movement.balance_after)
        }), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except RuntimeError as re:
        return jsonify({"error": str(re)}), 500
    except Exception:
        return jsonify({"error": "Error interno del servidor"}), 500