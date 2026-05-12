from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.utils.decorators import cashier_required
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.register_service import RegisterService
from app.services.product_service import ProductService
from app.models.domain import Order, OrderStatus, Payment, PaymentMethod, Table
from app.extensions import db
import decimal

pos_bp = Blueprint('pos', __name__, url_prefix='/pos')

@pos_bp.route('/dashboard')
@login_required
@cashier_required
def dashboard():
    tables = db.session.query(Table).order_by(Table.name).all()
    return render_template('pos/dashboard.html', tables=tables)

# --- Gestión de Caja (Apertura y Cierre) ---
@pos_bp.route('/register/open', methods=['GET'])
@login_required
@cashier_required
def open_register_form():
    try:
        session = RegisterService.get_active_session(user_id=str(current_user.id))
        if session:
            return redirect(url_for('pos.dashboard'))
        return render_template('pos/register_open.html')
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('pos.dashboard'))

@pos_bp.route('/register/open', methods=['POST'])
@login_required
@cashier_required
def open_register():
    try:
        opening_cash = decimal.Decimal(request.form.get('opening_cash', 0))
        RegisterService.open_register(user_id=str(current_user.id), opening_cash=opening_cash)
        flash('Caja abierta exitosamente.', 'success')
        return redirect(url_for('pos.dashboard'))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('pos.open_register_form'))

@pos_bp.route('/register/close', methods=['GET'])
@login_required
@cashier_required
def close_register_form():
    try:
        session = RegisterService.get_active_session(user_id=str(current_user.id))
        if not session:
            flash('No hay una sesión activa para cerrar.', 'warning')
            return redirect(url_for('pos.dashboard'))

        # Obtener todas las órdenes pagadas en esta sesión
        ventas_turno = db.session.query(Order).filter_by(
            register_session_id=session.id,
            status=OrderStatus.PAID
        ).all()

        # Desglose de pagos por método
        pagos_efectivo = decimal.Decimal('0.00')
        pagos_tarjeta = decimal.Decimal('0.00')
        pagos_transferencia = decimal.Decimal('0.00')

        for orden in ventas_turno:
            # Se asume que cada orden tiene un pago asociado
            pago = db.session.query(Payment).filter_by(order_id=orden.id).first()
            if pago:
                if pago.method == PaymentMethod.CASH:
                    pagos_efectivo += orden.total
                elif pago.method == PaymentMethod.CARD:
                    pagos_tarjeta += orden.total
                elif pago.method == PaymentMethod.TRANSFER:
                    pagos_transferencia += orden.total

        total_vendido = pagos_efectivo + pagos_tarjeta + pagos_transferencia
        # El efectivo esperado es únicamente: Fondo Inicial + Ventas en Efectivo
        efectivo_esperado = session.opening_cash + pagos_efectivo

        summary = {
            'opening_cash': session.opening_cash,
            'sales_total': total_vendido,
            'cash_sales': pagos_efectivo,
            'card_sales': pagos_tarjeta,
            'transfer_sales': pagos_transferencia,
            'expected_cash': efectivo_esperado
        }

        return render_template('pos/register_close.html', 
                               session=session, 
                               summary=summary)
    except Exception as e:
        flash(f"Error al cargar resumen: {str(e)}", 'danger')
        return redirect(url_for('pos.dashboard'))

@pos_bp.route('/register/close', methods=['POST'])
@login_required
@cashier_required
def close_register():
    try:
        session = RegisterService.get_active_session(user_id=str(current_user.id))
        if not session:
            flash('No hay una sesión de caja abierta.', 'warning')
            return redirect(url_for('pos.dashboard'))
            
        closing_cash = decimal.Decimal(request.form.get('closing_cash', 0))
        RegisterService.close_register(session_id=str(session.id), user_id=str(current_user.id), closing_cash=closing_cash)
        flash('Caja cerrada exitosamente.', 'success')
        return redirect(url_for('pos.dashboard'))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('pos.close_register_form'))

# --- Flujo POS (Crear Orden, Agregar Ítems) ---
@pos_bp.route('/order/create', methods=['POST'])
@login_required
@cashier_required
def create_order():
    try:
        session = RegisterService.get_active_session(user_id=str(current_user.id))
        if not session:
            if request.is_json:
                return jsonify({'error': 'No hay una sesión de caja abierta.'}), 400
            flash('Debes abrir la caja antes de crear una orden.', 'warning')
            return redirect(url_for('pos.dashboard'))
            
        data = request.get_json() or request.form.to_dict()
        table_id = data.get('table_id')
        customer_name = data.get('customer_name')
        notes = data.get('notes')
        
        order = OrderService.create_order(
            user_id=str(current_user.id),
            register_session_id=str(session.id),
            table_id=table_id,
            customer_name=customer_name,
            notes=notes
        )
        if request.is_json:
            return jsonify({'status': 'success', 'order_id': str(order.id)}), 201
        return redirect(url_for('pos.view_order', table_id=table_id or 'takeaway'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(str(e), 'danger')
        return redirect(url_for('pos.dashboard'))

@pos_bp.route('/order/table/<table_id>', methods=['GET'])
@login_required
@cashier_required
def view_order(table_id):
    try:
        session = RegisterService.get_active_session(user_id=str(current_user.id))
        if not session:
            flash('Debe abrir caja antes de tomar pedidos.', 'warning')
            return redirect(url_for('pos.open_register_form'))

        # Interceptar 'takeaway' para evitar errores de tipo UUID en PostgreSQL
        db_table_id = None if table_id == 'takeaway' else table_id
        table_name = "Para llevar"

        if db_table_id:
            table_obj = db.session.get(Table, db_table_id)
            table_name = table_obj.name if table_obj else "Desconocida"

        order = db.session.query(Order).filter_by(
            table_id=db_table_id,
            register_session_id=session.id,
            status=OrderStatus.OPEN
        ).first()

        if not order:
            order = OrderService.create_order(
                user_id=str(current_user.id),
                register_session_id=str(session.id),
                table_id=db_table_id
            )

        products = ProductService.get_all_products(is_active=True)
        
        return render_template('pos/order.html', 
                               order=order, 
                               products=products, 
                               table_name=table_name,
                               table_id=table_id)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('pos.dashboard'))

@pos_bp.route('/order/<order_id>/add', methods=['POST'])
@login_required
@cashier_required
def add_item(order_id):
    try:
        data = request.get_json() or request.form.to_dict()
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        item = OrderService.add_item_to_order(order_id=order_id, product_id=product_id, quantity=quantity)
        return jsonify({'status': 'success', 'item_id': str(item.id)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@pos_bp.route('/order-item/<item_id>/remove', methods=['POST'])
@login_required
@cashier_required
def remove_item(item_id):
    try:
        OrderService.remove_item_from_order(order_item_id=item_id)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@pos_bp.route('/order-item/<item_id>/update-quantity', methods=['POST'])
@login_required
@cashier_required
def update_item_quantity(item_id):
    try:
        data = request.get_json() or request.form.to_dict()
        quantity = int(data.get('quantity', 1))
        
        OrderService.update_item_quantity(order_item_id=item_id, new_quantity=quantity)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# --- Flujo de Pago ---
@pos_bp.route('/order/<order_id>/payment', methods=['GET'])
@login_required
@cashier_required
def payment_form(order_id):
    try:
        order = OrderService.get_order_by_id(order_id)
        if not order:
            flash('Orden no encontrada.', 'danger')
            return redirect(url_for('pos.dashboard'))
        methods = PaymentService.get_payment_methods()
        return render_template('pos/payment.html', order=order, methods=methods)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('pos.dashboard'))

@pos_bp.route('/order/<order_id>/pay', methods=['POST'])
@login_required
@cashier_required
def pay_order(order_id):
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            
        payment_method = data.get('payment_method')
        amount_received = decimal.Decimal(str(data.get('amount_received', 0)))
        reference = data.get('reference')
        
        result = PaymentService.process_payment(
            order_id=order_id, 
            payment_method=payment_method, 
            amount_received=amount_received,
            reference=reference
        )
        
        if request.is_json:
            return jsonify({'status': 'success', 'order_id': order_id, 'change': str(result['change'])}), 200
        else:
            flash(f"Pago procesado. Cambio: {result['change']}", 'success')
            return redirect(url_for('pos.receipt', order_id=order_id))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        else:
            flash(str(e), 'danger')
            return redirect(url_for('pos.payment_form', order_id=order_id))

@pos_bp.route('/receipt/<order_id>', methods=['GET'])
@login_required
@cashier_required
def receipt(order_id):
    try:
        receipt_data = PaymentService.generate_receipt(order_id)
        return render_template('pos/receipt.html', receipt=receipt_data)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('pos.dashboard'))

@pos_bp.route('/menu', methods=['GET'])
def get_menu():
    try:
        products = ProductService.get_all_products(is_active=True)
        menu = [{'id': str(p.id), 'name': p.name, 'price': str(p.price), 'stock': p.stock} for p in products]
        return jsonify(menu), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500