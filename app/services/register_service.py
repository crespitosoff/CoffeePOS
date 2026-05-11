# app/services/register_service.py  –  COF-37
from __future__ import annotations

import datetime
import decimal
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.domain import (
    CashMovement,
    MovementType,
    Order,
    OrderStatus,
    PaymentMethod,
    RegisterSession,
    RegisterStatus,
)


class RegisterService:
    """
    Gestiona el ciclo de vida de una sesión de caja (RegisterSession).

    Reglas críticas:
      - La tabla register_sessions usa opened_by / closed_by (FK a users.id),
        NO user_id.
      - opening_amount es NOT NULL.
      - Todo flujo de dinero se registra en cash_movements con MovementType.
      - Se opera SIEMPRE con decimal.Decimal para valores financieros.
    """

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    @staticmethod
    def get_active_session() -> Optional[RegisterSession]:
        """
        Retorna la sesión de caja actualmente abierta (status=OPEN), o None.
        La base de datos garantiza como máximo una sesión abierta a la vez
        mediante un índice parcial único.
        """
        return (
            db.session.query(RegisterSession)
            .filter(RegisterSession.status == RegisterStatus.OPEN)
            .first()
        )

    @staticmethod
    def get_session_by_id(session_id: str) -> Optional[RegisterSession]:
        """Retorna una sesión por UUID o None."""
        return db.session.get(RegisterSession, session_id)

    @staticmethod
    def get_session_summary(session_id: str) -> dict:
        """
        Genera un resumen de la sesión de caja:
          - Monto de apertura
          - Total de ventas en efectivo / tarjeta / transferencia
          - Total de retiros / depósitos manuales
          - Monto esperado en caja
          - Movimientos de caja
        """
        session = RegisterService.get_session_by_id(session_id)
        if not session:
            raise ValueError("Sesión de caja no encontrada.")

        # -- Totales de ventas por método de pago --
        orders_paid = (
            db.session.query(Order)
            .filter(
                Order.register_session_id == session_id,
                Order.status == OrderStatus.PAID,
            )
            .all()
        )

        sales_totals: dict[str, decimal.Decimal] = {
            PaymentMethod.CASH.value:     decimal.Decimal("0"),
            PaymentMethod.CARD.value:     decimal.Decimal("0"),
            PaymentMethod.TRANSFER.value: decimal.Decimal("0"),
        }
        total_sales = decimal.Decimal("0")

        for order in orders_paid:
            for payment in order.payments:
                amount = decimal.Decimal(str(payment.amount_paid))
                sales_totals[payment.method.value] = (
                    sales_totals.get(payment.method.value, decimal.Decimal("0")) + amount
                )
                total_sales += amount

        # -- Movimientos de caja --
        movements = (
            db.session.query(CashMovement)
            .filter_by(register_session_id=session_id)
            .order_by(CashMovement.created_at.asc())
            .all()
        )

        withdrawals = sum(
            decimal.Decimal(str(m.amount))
            for m in movements
            if m.movement_type == MovementType.WITHDRAWAL
        )
        manual_deposits = sum(
            decimal.Decimal(str(m.amount))
            for m in movements
            if m.movement_type == MovementType.DEPOSIT
            and m.reference_type != "order"  # excluir cobros de ventas
        )

        opening_amount = decimal.Decimal(str(session.opening_amount))
        # Efectivo esperado = apertura + ventas en efectivo + depósitos manuales - retiros
        expected_cash = (
            opening_amount
            + sales_totals[PaymentMethod.CASH.value]
            + manual_deposits
            - withdrawals
        )

        return {
            "session": session,
            "opening_amount": opening_amount,
            "total_sales": total_sales,
            "sales_by_method": sales_totals,
            "total_orders": len(orders_paid),
            "withdrawals": withdrawals,
            "manual_deposits": manual_deposits,
            "expected_cash": expected_cash.quantize(decimal.Decimal("0.01")),
            "closing_amount": (
                decimal.Decimal(str(session.closing_amount))
                if session.closing_amount is not None
                else None
            ),
            "difference": (
                decimal.Decimal(str(session.difference))
                if session.difference is not None
                else None
            ),
            "movements": movements,
        }

    # ------------------------------------------------------------------
    # Apertura de caja
    # ------------------------------------------------------------------

    @staticmethod
    def open_register(user_id: str, opening_cash: decimal.Decimal) -> RegisterSession:
        """
        Abre una nueva sesión de caja.

        Valida:
          - No haya otra sesión abierta.
          - El monto de apertura sea >= 0.

        Registra automáticamente un movimiento OPENING en cash_movements.
        """
        opening_cash = decimal.Decimal(str(opening_cash))
        if opening_cash < decimal.Decimal("0"):
            raise ValueError("El monto de apertura no puede ser negativo.")

        if RegisterService.get_active_session():
            raise ValueError(
                "Ya existe una sesión de caja abierta. "
                "Cierre la sesión activa antes de abrir una nueva."
            )

        try:
            session = RegisterSession(
                opened_by=user_id,
                opening_amount=opening_cash,
                status=RegisterStatus.OPEN,
                opened_at=datetime.datetime.utcnow(),
            )
            db.session.add(session)
            db.session.flush()  # obtener session.id sin commit

            # Registrar movimiento de apertura
            movement = CashMovement(
                register_session_id=str(session.id),
                user_id=user_id,
                movement_type=MovementType.OPENING,
                amount=opening_cash,
                balance_before=decimal.Decimal("0"),
                balance_after=opening_cash,
                description="Apertura de caja",
            )
            db.session.add(movement)
            db.session.commit()
            return session
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al abrir la caja: {e}") from e

    # ------------------------------------------------------------------
    # Cierre de caja
    # ------------------------------------------------------------------

    @staticmethod
    def close_register(
        session_id: str,
        user_id: str,
        closing_cash: decimal.Decimal,
    ) -> RegisterSession:
        """
        Cierra una sesión de caja activa.

        Calcula:
          - expected_amount: efectivo esperado según movimientos.
          - difference: closing_cash - expected_amount (positivo = sobrante).

        Registra un movimiento CLOSING en cash_movements.
        """
        closing_cash = decimal.Decimal(str(closing_cash))
        if closing_cash < decimal.Decimal("0"):
            raise ValueError("El monto de cierre no puede ser negativo.")

        session = RegisterService.get_session_by_id(session_id)
        if not session:
            raise ValueError("Sesión de caja no encontrada.")
        if session.status == RegisterStatus.CLOSED:
            raise ValueError("La sesión de caja ya está cerrada.")

        # Calcular expected_amount desde el resumen
        summary = RegisterService.get_session_summary(session_id)
        expected = summary["expected_cash"]
        difference = closing_cash - expected

        try:
            # Balance actual (último movimiento)
            last_movement: Optional[CashMovement] = (
                db.session.query(CashMovement)
                .filter_by(register_session_id=session_id)
                .order_by(CashMovement.created_at.desc())
                .first()
            )
            balance_before = (
                decimal.Decimal(str(last_movement.balance_after))
                if last_movement
                else decimal.Decimal("0")
            )

            movement = CashMovement(
                register_session_id=session_id,
                user_id=user_id,
                movement_type=MovementType.CLOSING,
                amount=closing_cash,
                balance_before=balance_before,
                balance_after=closing_cash,
                description=(
                    f"Cierre de caja. "
                    f"Real: {closing_cash} | Esperado: {expected} | "
                    f"Diferencia: {difference}"
                ),
            )
            db.session.add(movement)

            session.closed_by = user_id
            session.closing_amount = closing_cash
            session.expected_amount = expected
            session.difference = difference.quantize(decimal.Decimal("0.01"))
            session.status = RegisterStatus.CLOSED
            session.closed_at = datetime.datetime.utcnow()

            db.session.commit()
            return session
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al cerrar la caja: {e}") from e
