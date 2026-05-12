# app/services/payment_service.py  –  COF-35
from __future__ import annotations
import decimal
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db
from app.models.domain import (
    Order, OrderStatus,
    Payment, PaymentMethod, StoreSetting,
)
from app.services.cash_movement_service import CashMovementService


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
        Si el método es CASH delega el registro del ingreso a CashMovementService
        (centralización contable).
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
                change=change,
                reference=reference,
            )
            db.session.add(payment)

            order.status = OrderStatus.PAID
            order.closed_at = datetime.now(timezone.utc)
            db.session.flush()

            # Delegar el ingreso de efectivo a CashMovementService.
            # Solo se registra movimiento para pagos en CASH; tarjeta/transferencia
            # no afectan el saldo físico de la caja.
            if method == PaymentMethod.CASH and order.register_session_id:
                # record_deposit hace su propio commit. Pasamos la referencia
                # de la orden para trazabilidad antirrobo (reference_type='order').
                PaymentService._record_cash_income(
                    session_id=str(order.register_session_id),
                    user_id=str(order.user_id),
                    amount=order_total,
                    order_id=str(order.id),
                )
            else:
                # Para métodos no-efectivo solo necesitamos el commit del pago/orden.
                db.session.commit()

            return {"payment": payment, "order": order, "change": change}

        except (ValueError, RuntimeError):
            db.session.rollback()
            raise
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

        utc_time_created_at = order.created_at.replace(tzinfo=timezone.utc)
        formatted_date_created_at = utc_time_created_at.strftime("%d-%m-%Y %H:%M")

        utc_time_closed_at = order.closed_at.replace(tzinfo=timezone.utc)
        formatted_date_closed_at = utc_time_closed_at.strftime("%d-%m-%Y %H:%M")

        amount_paid = decimal.Decimal(str(payment.amount_paid)) if payment else decimal.Decimal("0")
        total_order = decimal.Decimal(str(order.total))
        change = amount_paid - total_order if amount_paid > total_order else decimal.Decimal("0")

        return {
            "store": {
                "business_name":  setting.business_name  if setting else "CoffeePOS",
                "address":        setting.address         if setting else "",
                "phone":          setting.phone           if setting else "",
                "tax_id":         setting.tax_id          if setting else "",
                "receipt_footer": setting.receipt_footer  if setting else "",
                "currency":       setting.currency        if setting else "COP",
                "invoice_prefix": setting.invoice_prefix  if setting else "",
            },
            "order": {
                "id":            str(order.id),
                "customer_name": order.customer_name,
                "table":         order.table.name if order.table else None,
                "cashier":       order.user.username if order.user else "Desconocido",
                "subtotal":      decimal.Decimal(str(order.subtotal)),
                "tax":           decimal.Decimal(str(order.tax)),
                "total":         decimal.Decimal(str(order.total)),
                "created_at":    formatted_date_created_at,
                "closed_at":     formatted_date_closed_at,
                "notes":         order.notes,
            },
            "payment": {
                "method":      payment.method.value if payment else "N/A",
                "amount_paid": amount_paid,
                "reference":   payment.reference if payment else None,
                "change":      change,
            },
            "items": items_data,
        }

    @staticmethod
    def _record_cash_income(
        session_id: str, user_id: str,
        amount: decimal.Decimal, order_id: str,
    ) -> None:
        """
        Registra ingreso de efectivo por venta delegando a CashMovementService.record_deposit.
        El método calcula el balance automáticamente y hace commit.
        Se etiqueta con reference_type='order' para excluirlo del cálculo de
        depósitos manuales en get_session_summary().

        NOTA: CashMovementService.record_deposit hace su propio commit, lo que
        también persiste el Payment y la Order actualizados en el flush previo.
        """
        amount = decimal.Decimal(str(amount))
        description = f"Ingreso por venta – Orden {order_id[:8]}"

        # record_deposit valida monto > 0, calcula balance y hace commit.
        movement = CashMovementService.record_deposit(
            session_id=session_id,
            user_id=user_id,
            amount=amount,
            description=description,
        )

        # Etiquetar con referencia de la orden para trazabilidad antirrobo.
        # Como record_deposit ya hizo commit, necesitamos un update posterior.
        try:
            movement.reference_type = "order"
            movement.reference_id = order_id
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al etiquetar movimiento de venta: {e}") from e
