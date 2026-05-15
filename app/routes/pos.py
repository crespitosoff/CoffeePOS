from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session as flask_session
from flask_login import login_required, current_user
from app.utils.decorators import cashier_required
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.register_service import RegisterService
from app.services.product_service import ProductService
from app.models.domain import Order, OrderStatus, Payment, PaymentMethod, Table, Category, GenericStatus
from app.extensions import db
import decimal
import datetime

pos_bp = Blueprint("pos", __name__, url_prefix="/pos")


@pos_bp.route("/dashboard")
@login_required
@cashier_required
def dashboard():
    from app.models.domain import OrderStatus as _OS
    raw_tables = db.session.query(Table).order_by(Table.name).all()
    session    = RegisterService.get_active_session(user_id=str(current_user.id))

    # Determinar qué mesas tienen una orden OPEN (Global)
    open_orders = (
        db.session.query(Order)
        .filter(
            Order.status == _OS.OPEN,
            Order.table_id.isnot(None),
        )
        .all()
    )
    occupied_table_ids = {str(o.table_id) for o in open_orders}

    # Construir lista enriquecida con estado de ocupación
    tables = [
        {
            "id":       str(t.id),
            "name":     t.name,
            "capacity": t.capacity,
            "status":   "occupied" if str(t.id) in occupied_table_ids else "available",
        }
        for t in raw_tables
    ]

    return render_template("pos/dashboard.html", tables=tables, session=session)

@pos_bp.route("/api/tables/status", methods=["GET"])
@login_required
@cashier_required
def api_tables_status():
    from app.models.domain import OrderStatus as _OS
    raw_tables = db.session.query(Table).all()
    
    open_orders = db.session.query(Order).filter(
        Order.status == _OS.OPEN,
        Order.table_id.isnot(None)
    ).all()
    occupied_table_ids = {str(o.table_id) for o in open_orders}
        
    status_data = {
        str(t.id): "occupied" if str(t.id) in occupied_table_ids else "available"
        for t in raw_tables
    }
    return jsonify(status_data)


# --- Gestión de Caja (Apertura y Cierre) ---
@pos_bp.route("/register/open", methods=["GET"])
@login_required
@cashier_required
def open_register_form():
    try:
        session = RegisterService.get_active_session(user_id=str(current_user.id))
        if session:
            return redirect(url_for("pos.dashboard"))
        return render_template("pos/register_open.html", current_datetime=datetime.datetime.now())
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("pos.dashboard"))


@pos_bp.route("/register/open", methods=["POST"])
@login_required
@cashier_required
def open_register():
    try:
        opening_amount = decimal.Decimal(request.form.get("opening_amount", 0))
        RegisterService.open_register(
            user_id=str(current_user.id), opening_amount=opening_amount
        )
        flash("Caja abierta exitosamente.", "success")
        return redirect(url_for("pos.dashboard"))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("pos.open_register_form"))


@pos_bp.route("/register/close", methods=["GET"])
@login_required
@cashier_required
def close_register_form():
    try:
        session = RegisterService.get_active_session(user_id=str(current_user.id))
        if not session:
            flash("No hay una sesión activa para cerrar.", "warning")
            return redirect(url_for("pos.dashboard"))

        # Advertir al cajero sobre órdenes OPEN pendientes antes de mostrar el formulario
        pending_orders = (
            db.session.query(Order)
            .filter_by(register_session_id=session.id, status=OrderStatus.OPEN)
            .all()
        )

        # Obtener todas las órdenes pagadas en esta sesión para el resumen
        ventas_turno = (
            db.session.query(Order)
            .filter_by(register_session_id=session.id, status=OrderStatus.PAID)
            .all()
        )

        pagos_efectivo     = decimal.Decimal("0.00")
        pagos_tarjeta      = decimal.Decimal("0.00")
        pagos_transferencia = decimal.Decimal("0.00")

        for orden in ventas_turno:
            pago = db.session.query(Payment).filter_by(order_id=orden.id).first()
            if pago:
                if pago.method == PaymentMethod.CASH:
                    pagos_efectivo += decimal.Decimal(str(orden.total))
                elif pago.method == PaymentMethod.CARD:
                    pagos_tarjeta += decimal.Decimal(str(orden.total))
                elif pago.method == PaymentMethod.TRANSFER:
                    pagos_transferencia += decimal.Decimal(str(orden.total))

        total_vendido     = pagos_efectivo + pagos_tarjeta + pagos_transferencia
        efectivo_esperado = decimal.Decimal(str(session.opening_amount)) + pagos_efectivo

        summary = {
            "opening_amount":    session.opening_amount,
            "sales_total":       total_vendido,
            "cash_sales":        pagos_efectivo,
            "card_sales":        pagos_tarjeta,
            "transfer_sales":    pagos_transferencia,
            "expected_cash":     efectivo_esperado,
        }

        return render_template(
            "pos/register_close.html",
            session=session,
            summary=summary,
            pending_orders=pending_orders,
            current_datetime=datetime.datetime.now()
        )
    except Exception as e:
        flash(f"Error al cargar resumen: {str(e)}", "danger")
        return redirect(url_for("pos.dashboard"))


@pos_bp.route("/register/close", methods=["POST"])
@login_required
@cashier_required
def close_register():
    try:
        session = RegisterService.get_active_session(user_id=str(current_user.id))
        if not session:
            flash("No hay una sesión de caja abierta.", "warning")
            return redirect(url_for("pos.dashboard"))

        closing_amount = decimal.Decimal(request.form.get("closing_amount", 0))
        RegisterService.close_register(
            session_id=str(session.id),
            user_id=str(current_user.id),
            closing_amount=closing_amount,
        )
        flash("Caja cerrada exitosamente.", "success")
        return redirect(url_for("pos.dashboard"))
    except ValueError as e:
        flash(str(e), "warning")
        return redirect(url_for("pos.close_register_form"))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("pos.close_register_form"))


# --- Flujo POS (Crear Orden, Agregar Ítems) ---
@pos_bp.route("/order/create", methods=["POST"])
@login_required
@cashier_required
def create_order():
    try:
        session = RegisterService.get_active_session(user_id=str(current_user.id))
        if not session:
            if request.is_json:
                return jsonify({"error": "No hay una sesión de caja abierta."}), 400
            flash("Debes abrir la caja antes de crear una orden.", "warning")
            return redirect(url_for("pos.dashboard"))

        data = request.get_json() or request.form.to_dict()
        table_id      = data.get("table_id")
        customer_name = data.get("customer_name")
        notes         = data.get("notes")

        order = OrderService.create_order(
            user_id=str(current_user.id),
            register_session_id=str(session.id),
            table_id=table_id,
            customer_name=customer_name,
            notes=notes,
        )
        if request.is_json:
            return jsonify({"status": "success", "order_id": str(order.id)}), 201
        return redirect(url_for("pos.view_order", table_id=table_id or "takeaway"))
    except Exception as e:
        if request.is_json:
            return jsonify({"error": str(e)}), 400
        flash(str(e), "danger")
        return redirect(url_for("pos.dashboard"))


@pos_bp.route("/order/table/<table_id>", methods=["GET"])
@login_required
@cashier_required
def view_order(table_id):
    try:
        session_reg = RegisterService.get_active_session(user_id=str(current_user.id))
        is_admin = flask_session.get('role') == 'ADMIN'
        
        if not session_reg and not is_admin:
            flash("Debe abrir caja antes de tomar pedidos.", "warning")
            return redirect(url_for("pos.open_register_form"))

        read_only = not session_reg

        db_table_id = None if table_id == "takeaway" else table_id
        table_name  = "Para llevar"

        if db_table_id:
            table_obj  = db.session.get(Table, db_table_id)
            table_name = table_obj.name if table_obj else "Desconocida"

        order = (
            db.session.query(Order)
            .filter_by(
                table_id=db_table_id,
                status=OrderStatus.OPEN,
            )
            .first()
        )

        products = ProductService.get_all_products(is_active=True)

        # Categorías y mesas para filtros y table switcher
        categories = (
            db.session.query(Category)
            .filter_by(status=GenericStatus.ACTIVE)
            .order_by(Category.name)
            .all()
        )
        all_tables = db.session.query(Table).order_by(Table.name).all()

        return render_template(
            "pos/order.html",
            order=order,
            products=products,
            table_name=table_name,
            table_id=table_id,
            categories=categories,
            tables=all_tables,
            read_only=read_only,
        )
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("pos.dashboard"))


@pos_bp.route("/order/add-item", methods=["POST"])
@login_required
@cashier_required
def add_item():
    try:
        session_reg = RegisterService.get_active_session(user_id=str(current_user.id))
        if not session_reg:
             return jsonify({"error": "No hay sesión abierta."}), 400

        data       = request.get_json() or request.form.to_dict()
        order_id   = data.get("order_id")
        product_id = data.get("product_id")
        quantity   = int(data.get("quantity", 1))
        table_id   = data.get("table_id")

        if not order_id:
            db_table_id = None if table_id == "takeaway" else table_id
            order = OrderService.create_order(
                user_id=str(current_user.id),
                register_session_id=str(session_reg.id),
                table_id=db_table_id
            )
            order_id = str(order.id)

        item = OrderService.add_item_to_order(
            order_id=order_id, product_id=product_id, quantity=quantity
        )
        return jsonify({"status": "success", "item_id": str(item.id), "order_id": order_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@pos_bp.route("/order-item/<item_id>/remove", methods=["POST"])
@login_required
@cashier_required
def remove_item(item_id):
    try:
        OrderService.remove_item_from_order(order_item_id=item_id)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@pos_bp.route("/order-item/<item_id>/update-quantity", methods=["POST"])
@login_required
@cashier_required
def update_item_quantity(item_id):
    try:
        data     = request.get_json() or request.form.to_dict()
        quantity = int(data.get("quantity", 1))

        OrderService.update_item_quantity(order_item_id=item_id, new_quantity=quantity)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --- Cancelación de Orden (Paso 1.2) ---
@pos_bp.route("/order/<order_id>/cancel", methods=["POST"])
@login_required
@cashier_required
def cancel_order(order_id):
    """
    Cancela una orden OPEN:
      - Devuelve stock a todos los productos.
      - Libera la mesa (table_id = None).
      - Cambia estado a CANCELLED.
    Responde JSON si la petición es AJAX, redirige si es form POST.
    """
    try:
        order = OrderService.cancel_order(order_id=order_id)

        if request.is_json:
            return jsonify({
                "status": "cancelled",
                "order_id": str(order.id),
                "redirect": url_for("pos.dashboard"),
            }), 200

        flash("Orden cancelada. El stock ha sido repuesto.", "success")
        return redirect(url_for("pos.dashboard"))

    except ValueError as e:
        if request.is_json:
            return jsonify({"error": str(e)}), 400
        flash(str(e), "warning")
        return redirect(url_for("pos.dashboard"))
    except Exception as e:
        if request.is_json:
            return jsonify({"error": str(e)}), 500
        flash(str(e), "danger")
        return redirect(url_for("pos.dashboard"))


# --- Flujo de Pago ---
@pos_bp.route("/order/<order_id>/payment", methods=["GET"])
@login_required
@cashier_required
def payment_form(order_id):
    try:
        order = OrderService.get_order_by_id(order_id)
        if not order:
            flash("Orden no encontrada.", "danger")
            return redirect(url_for("pos.dashboard"))
        methods = PaymentService.get_payment_methods()
        return render_template("pos/payment.html", order=order, methods=methods)
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("pos.dashboard"))


@pos_bp.route("/order/<order_id>/pay", methods=["POST"])
@login_required
@cashier_required
def pay_order(order_id):
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        payment_method  = data.get("payment_method")
        amount_received = decimal.Decimal(str(data.get("amount_received", 0)))
        reference       = data.get("reference")

        session_reg = RegisterService.get_active_session(user_id=str(current_user.id))
        if not session_reg:
            if request.is_json:
                return jsonify({"error": "No hay una sesión de caja abierta."}), 400
            flash("No hay una sesión de caja abierta.", "warning")
            return redirect(url_for("pos.dashboard"))

        result = PaymentService.process_payment(
            order_id=order_id,
            payment_method=payment_method,
            amount_received=amount_received,
            reference=reference,
            session_id=str(session_reg.id)
        )

        if request.is_json:
            return jsonify({
                "status":   "success",
                "order_id": order_id,
                "change":   str(result["change"]),
            }), 200
        else:
            flash(f"Pago procesado. Cambio: ${result['change']:,.2f}", "success")
            return redirect(url_for("pos.receipt", order_id=order_id))

    except ValueError as e:
        if request.is_json:
            return jsonify({"error": str(e)}), 400
        flash(str(e), "warning")
        return redirect(url_for("pos.payment_form", order_id=order_id))
    except Exception as e:
        if request.is_json:
            return jsonify({"error": str(e)}), 500
        flash(str(e), "danger")
        return redirect(url_for("pos.payment_form", order_id=order_id))


@pos_bp.route("/receipt/<order_id>", methods=["GET"])
@login_required
@cashier_required
def receipt(order_id):
    try:
        receipt_data = PaymentService.generate_receipt(order_id)
        return render_template("pos/receipt.html", receipt=receipt_data)
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("pos.dashboard"))


@pos_bp.route("/menu", methods=["GET"])
def get_menu():
    try:
        products = ProductService.get_all_products(is_active=True)
        menu = [
            {"id": str(p.id), "name": p.name, "price": str(p.price), "stock": p.stock}
            for p in products
        ]
        return jsonify(menu), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
