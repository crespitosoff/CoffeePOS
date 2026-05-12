import decimal
from app.services.register_service import RegisterService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.models.domain import User, Product, Table
from app.extensions import db

try:
    user = db.session.query(User).first()
    product = db.session.query(Product).first()
    table = db.session.query(Table).first()

    table_id = str(table.id) if table else None

    # INYECCIÓN DE STOCK
    product.stock = 50
    db.session.commit()
    print(f"[OK] Stock actualizado para {product.name}: {product.stock}")

    # 2. Abrir Caja
    opening_amount = decimal.Decimal("100000.00")
    session = RegisterService.open_register(
        user_id=str(user.id), opening_cash=opening_amount
    )
    print(f"[OK] Caja abierta. ID: {session.id}")

    # 3. Crear Orden
    order = OrderService.create_order(
        user_id=str(user.id),
        register_session_id=str(session.id),
        table_id=str(table_id),
    )
    print(f"[OK] Orden creada. ID: {order.id}")

    # 4. Agregar Producto a la Orden
    item = OrderService.add_item_to_order(
        order_id=str(order.id), product_id=str(product.id), quantity=2
    )
    db.session.refresh(order)
    print(f"[OK] Item agregado. Total actual de la orden: {order.total}")

    # 5. Procesar Pago (Firma corregida)
    payment_data = PaymentService.process_payment(
        order_id=str(order.id), payment_method="cash", amount_received=order.total
    )
    db.session.refresh(order)
    print(f"[OK] Pago procesado. Status de orden: {order.status.value}")

    # 6. Cerrar Caja
    expected_amount = opening_amount + order.total
    closed_session = RegisterService.close_register(
        session_id=str(session.id), user_id=str(user.id), closing_cash=expected_amount
    )
    print(f"[OK] Caja cerrada. Diferencia: {closed_session.difference}")

except Exception as e:
    print(f"[ERROR CRÍTICO] {type(e).__name__}: {str(e)}")
    db.session.rollback()
