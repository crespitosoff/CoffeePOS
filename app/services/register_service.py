# app/services/register_service.py  –  COF-37
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError, IntegrityError

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
from app.services.cash_movement_service import CashMovementService


class RegisterService:
    """
    Gestiona el ciclo de vida de una sesión de caja (RegisterSession).

    Reglas críticas:
      - La tabla register_sessions usa opened_by / closed_by (FK a users.id),
        NO user_id.
      - opening_amount es NOT NULL.
      - Todo flujo de dinero se delega a CashMovementService (centralización contable).
      - Se opera SIEMPRE con Decimal para valores financieros.
    """

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    @staticmethod
    def get_active_session(user_id) -> Optional[RegisterSession]:
        """
        Retorna la sesión de caja actualmente abierta (status=OPEN), o None.
        La base de datos garantiza como máximo una sesión abierta a la vez
        mediante un índice parcial único.
        """
        return (
            db.session.query(RegisterSession)
            .filter_by(opened_by=user_id, status=RegisterStatus.OPEN)
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

        sales_totals: dict[str, Decimal] = {
            PaymentMethod.CASH.value: Decimal("0"),
            PaymentMethod.CARD.value: Decimal("0"),
            PaymentMethod.TRANSFER.value: Decimal("0"),
        }
        total_sales = Decimal("0")

        for order in orders_paid:
            for payment in order.payments:
                amount = Decimal(str(payment.amount_paid))
                sales_totals[payment.method.value] = (
                    sales_totals.get(payment.method.value, Decimal("0")) + amount
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
            abs(Decimal(str(m.amount)))
            for m in movements
            if m.movement_type == MovementType.WITHDRAWAL
        )
        manual_deposits = sum(
            Decimal(str(m.amount))
            for m in movements
            if m.movement_type == MovementType.DEPOSIT
            and m.reference_type != "order"  # excluir cobros de ventas
        )

        opening_amount = Decimal(str(session.opening_amount))
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
            "expected_cash": expected_cash.quantize(Decimal("0.01")),
            "closing_amount": (
                Decimal(str(session.closing_amount))
                if session.closing_amount is not None
                else None
            ),
            "difference": (
                Decimal(str(session.difference))
                if session.difference is not None
                else None
            ),
            "movements": movements,
        }

    # ------------------------------------------------------------------
    # Apertura de caja
    # ------------------------------------------------------------------

    @staticmethod
    def open_register(user_id: str, opening_amount: Decimal) -> RegisterSession:
        """
        Abre una nueva sesión de caja.

        Valida:
          - No haya otra sesión abierta por este usuario.
          - El monto de apertura sea >= 0.

        Delega el movimiento OPENING a CashMovementService (centralización contable).
        """
        opening_amount = Decimal(str(opening_amount))
        if opening_amount < Decimal("0"):
            raise ValueError("El monto de apertura no puede ser negativo.")

        if RegisterService.get_active_session(user_id):
            raise ValueError(
                "El usuario ya tiene una sesión de caja abierta. "
                "Cierre la sesión activa antes de abrir una nueva."
            )

        try:
            session = RegisterSession(
                opened_by=user_id,
                opening_amount=opening_amount,
                status=RegisterStatus.OPEN,
                opened_at=datetime.datetime.now(datetime.timezone.utc),
            )
            db.session.add(session)
            db.session.flush()  # obtener session.id sin commit

            # Delegar el registro del movimiento de apertura a CashMovementService.
            # _execute_movement hace su propio commit; aquí flush es suficiente
            # para asegurar el orden; usamos add+flush para que el session.id exista.
            CashMovementService.record_opening(
                session_id=str(session.id),
                user_id=user_id,
                amount=opening_amount,
            )
            # record_opening ya hace commit internamente; la sesión ya quedó guardada.
            return session

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(
                f"Error de integridad: Violación de sesión única activa. - {e}"
            ) from e
        except (ValueError, RuntimeError):
            db.session.rollback()
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al abrir la caja: {e}") from e
        except Exception as e:
            db.session.rollback()
            raise e

    # ------------------------------------------------------------------
    # Cierre de caja
    # ------------------------------------------------------------------

    @staticmethod
    def close_register(
        session_id: str,
        user_id: str,
        closing_amount: Decimal,
    ) -> RegisterSession:
        """
        Cierra una sesión de caja activa.

        Calcula:
          - expected_cash: efectivo esperado según movimientos.
          - difference: closing_amount - expected_cash (positivo = sobrante).

        Delega el movimiento CLOSING a CashMovementService (centralización contable).
        Valida que no existan órdenes en estado OPEN asociadas a la sesión.
        """
        closing_amount = Decimal(str(closing_amount))
        if closing_amount < Decimal("0"):
            raise ValueError("El monto de cierre no puede ser negativo.")

        session = RegisterService.get_session_by_id(session_id)
        if not session:
            raise ValueError("Sesión de caja no encontrada.")
        if session.status == RegisterStatus.CLOSED:
            raise ValueError("La sesión de caja ya está cerrada.")
        if str(session.opened_by) != str(user_id):
            raise ValueError("No puedes cerrar la caja de otro usuario.")

        # Prevenir cierre si existen órdenes sin finalizar asociadas a esta sesión
        pending_orders_count = (
            db.session.query(Order)
            .filter_by(register_session_id=session.id, status=OrderStatus.OPEN)
            .count()
        )
        if pending_orders_count > 0:
            raise ValueError(
                f"No se puede cerrar la caja. "
                f"Hay {pending_orders_count} orden(es) pendiente(s). "
                f"Cancélalas o cóbralas antes de cerrar."
            )

        # Calcular expected_cash desde el resumen
        summary = RegisterService.get_session_summary(session_id)
        expected = summary["expected_cash"]
        difference = (closing_amount - expected).quantize(Decimal("0.01"))

        try:
            # ORDEN CRÍTICO:
            # 1. Registrar el movimiento CLOSING primero, mientras la sesión sigue OPEN.
            #    CashMovementService._validate_session_open requiere status=OPEN.
            #    record_closing() hace commit internamente → el movimiento queda guardado.
            CashMovementService.record_closing(
                session_id=session_id,
                user_id=user_id,
                amount=closing_amount,
                expected=expected,
            )

            # 2. Refrescar el objeto sesión (el commit de record_closing lo dejó en
            #    estado limpio) y actualizar los campos de cierre.
            session = RegisterService.get_session_by_id(session_id)
            session.closed_by      = user_id
            session.closing_amount = closing_amount
            session.expected_amount = expected       # columna correcta del modelo
            session.difference     = difference
            session.status         = RegisterStatus.CLOSED
            session.closed_at      = datetime.datetime.now(datetime.timezone.utc)
            db.session.commit()
            return session

        except (ValueError, RuntimeError):
            db.session.rollback()
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al cerrar la caja: {e}") from e
        except Exception as e:
            db.session.rollback()
            raise e
