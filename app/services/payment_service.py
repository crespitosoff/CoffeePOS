# app/services/payment_service.py  –  COF-35
from __future__ import annotations
import datetime
import decimal
from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db
from app.models.domain import (
    CashMovement, MovementType, Order, OrderStatus,
    Payment, PaymentMethod, StoreSetting,
)


class PaymentService:
    """Encapsula la lógica de procesamiento de pagos."""

    @staticmethod
    def get_payment_methods() -> List[dict]:
        return [
            {"value": PaymentMethod.CASH.value,     "label": "Efectivo"},
            {"value": PaymentMethod.CARD.value,      "label": "Tarjeta"},
            {"value": PaymentMethod.TRANSFER.value,  "label": "Transferencia"},
        ]

    @staticmethod
    def process_payment(
        order_id: str,
        payment_method: str,
        amount_received: decimal.Decimal,
        reference: Optional[str] = None,
    ) -> dict:
        """
        Procesa el pago de una orden y la cierra.
        Solo órdenes con status OPEN pueden pagarse.
        amount_received debe ser >= total de la orden.
        Si el método es CASH registra un movimiento en cash_movements.
        """
        amount_received = decimal.Decimal(str(amount_received))

        try:
            method = PaymentMethod(payment_method)
        except ValueError:
            raise ValueError(f"Método de pago inválido: '{payment_method}'.")

        order: Optional[Order] = db.session.get(Order, order_id)
        if not order:
            raise ValueError("Orden no encontrada.")
        if order.status != OrderStatus.OPEN:
            raise ValueError(
                f"Solo se pueden pagar órdenes en estado 'open'. "
                f"Estado actual: '{order.status.value}'."
            )
        if not order.order_items:
            raise ValueError("No se puede pagar una orden sin ítems.")

        order_total = decimal.Decimal(str(order.total))
        if amount_received < order_total:
            raise ValueError(
                f"El monto recibido ({amount_received}) es menor que el total ({order_total})."
            )

        change = (amount_received - order_total).quantize(decimal.Decimal("0.01"))

        try:
            payment = Payment(
                order_id=order_id,
                register_session_id=order.register_session_id,
                method=method,
                amount_paid=order_total,
                reference=reference,
            )
            db.session.add(payment)

            order.status = OrderStatus.PAID
            order.closed_at = datetime.datetime.utcnow()

            if method == PaymentMethod.CASH and order.register_session_id:
                PaymentService._record_cash_income(
                    session_id=str(order.register_session_id),
                    user_id=str(order.user_id),
                    amount=order_total,
                    order_id=str(order.id),
                )

            db.session.commit()
            return {"payment": payment, "order": order, "change": change}
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al procesar el pago: {e}") from e

    @staticmethod
    def generate_receipt(order_id: str) -> dict:
        """Genera un dict con todos los datos necesarios para imprimir un recibo."""
        order: Optional[Order] = db.session.get(Order, order_id)
        if not order:
            raise ValueError("Orden no encontrada.")
        if order.status != OrderStatus.PAID:
            raise ValueError("Solo se puede generar recibo de órdenes pagadas.")

        setting = db.session.query(StoreSetting).first()
        payment: Optional[Payment] = (
            db.session.query(Payment)
            .filter(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
            .first()
        )

        items_data = [
            {
                "product_name": (item.product.name if item.product else "Producto eliminado"),
                "quantity": item.quantity,
                "base_price": decimal.Decimal(str(item.base_price)),
                "subtotal":   decimal.Decimal(str(item.subtotal)),
                "notes": item.notes,
            }
            for item in order.order_items
        ]

        return {
            "store": {
                "business_name":  setting.business_name  if setting else "CoffeePOS",
                "address":        setting.address         if setting else "",
                "phone":          setting.phone           if setting else "",
                "tax_id":         setting.tax_id          if setting else "",
                "receipt_footer": setting.receipt_footer  if setting else "",
                "currency":       setting.currency        if setting else "COP",
            },
            "order": {
                "id":            str(order.id),
                "customer_name": order.customer_name,
                "table":         order.table.name if order.table else None,
                "cashier":       order.user.username if order.user else "Desconocido",
                "subtotal":      decimal.Decimal(str(order.subtotal)),
                "tax":           decimal.Decimal(str(order.tax)),
                "total":         decimal.Decimal(str(order.total)),
                "created_at":    order.created_at,
                "closed_at":     order.closed_at,
                "notes":         order.notes,
            },
            "payment": {
                "method":      payment.method.value if payment else "N/A",
                "amount_paid": decimal.Decimal(str(payment.amount_paid)) if payment else decimal.Decimal("0"),
                "reference":   payment.reference if payment else None,
            },
            "items": items_data,
        }

    @staticmethod
    def _record_cash_income(
        session_id: str, user_id: str,
        amount: decimal.Decimal, order_id: str,
    ) -> None:
        """Registra ingreso de efectivo en cash_movements (sin commit propio)."""
        amount = decimal.Decimal(str(amount))
        last = (
            db.session.query(CashMovement)
            .filter_by(register_session_id=session_id)
            .order_by(CashMovement.created_at.desc())
            .first()
        )
        balance_before = decimal.Decimal(str(last.balance_after)) if last else decimal.Decimal("0")
        balance_after  = balance_before + amount

        movement = CashMovement(
            register_session_id=session_id,
            user_id=user_id,
            movement_type=MovementType.DEPOSIT,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type="order",
            reference_id=order_id,
            description=f"Ingreso por venta – Orden {order_id[:8]}",
        )
        db.session.add(movement)
