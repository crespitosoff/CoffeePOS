# app/services/report_service.py  –  COF-63 / COF-64 / COF-65
# Servicio de trazabilidad antirrobo y auditoría de caja
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import List, Optional

from app.extensions import db
from app.models.domain import (
    CashMovement,
    MovementType,
    Order,
    OrderStatus,
    PaymentMethod,
    RegisterSession,
    RegisterStatus,
    User,
)


# ---------------------------------------------------------------------------
# Umbral para marcar un retiro como "sospechoso"
# Se puede mover a store_settings en el futuro.
# ---------------------------------------------------------------------------
SUSPICIOUS_WITHDRAWAL_THRESHOLD = Decimal("50000")  # COP


class ReportService:
    """
    Genera reportes de auditoría y trazabilidad para el panel del administrador.

    Todos los métodos retornan dicts serializables (sin objetos ORM en el nivel
    raíz) para facilitar la renderización en Jinja2 y la futura serialización JSON.
    """

    # ------------------------------------------------------------------
    # Historial de sesiones de caja (Panel Antirrobo)
    # ------------------------------------------------------------------

    @staticmethod
    def get_register_audit_trail(
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
    ) -> List[dict]:
        """
        Retorna el historial completo de sesiones de caja dentro del rango de fechas,
        enriquecido con:
          - Nombre del cajero que abrió y cerró
          - Montos de apertura, cierre y esperado
          - Diferencia (descuadre): marcada como 'ok', 'surplus' o 'deficit'
          - Duración de la sesión
          - Totales de venta por método de pago
          - Movimientos de retiro sospechosos
        """
        query = db.session.query(RegisterSession)

        if start_date:
            start_dt = datetime.datetime.combine(start_date, datetime.time.min)
            query = query.filter(RegisterSession.opened_at >= start_dt)
        if end_date:
            end_dt = datetime.datetime.combine(end_date, datetime.time.max)
            query = query.filter(RegisterSession.opened_at <= end_dt)

        sessions = query.order_by(RegisterSession.opened_at.desc()).all()

        result = []
        for session in sessions:
            result.append(ReportService._build_session_audit(session))
        return result

    @staticmethod
    def get_session_detail(session_id: str) -> dict:
        """
        Retorna el detalle completo de una sesión específica:
          - Todos los movimientos de caja con tipo y usuario
          - Todas las órdenes (pagadas, canceladas)
          - Desglose de pagos por método
        """
        session = db.session.get(RegisterSession, session_id)
        if not session:
            raise ValueError(f"Sesión '{session_id}' no encontrada.")

        audit = ReportService._build_session_audit(session)

        # Detalle de órdenes de la sesión
        orders = (
            db.session.query(Order)
            .filter(Order.register_session_id == session_id)
            .order_by(Order.created_at.asc())
            .all()
        )
        orders_detail = []
        for o in orders:
            payment = o.payments[0] if o.payments else None
            orders_detail.append(
                {
                    "id": str(o.id),
                    "status": o.status.value,
                    "customer_name": o.customer_name or "Sin nombre",
                    "table": o.table.name if o.table else "Para llevar",
                    "total": Decimal(str(o.total)),
                    "payment_method": payment.method.value if payment else None,
                    "created_at": o.created_at,
                    "closed_at": o.closed_at,
                    "cashier": o.user.username if o.user else "Desconocido",
                }
            )

        # Detalle de movimientos de caja
        movements = (
            db.session.query(CashMovement)
            .filter_by(register_session_id=session_id)
            .order_by(CashMovement.created_at.asc())
            .all()
        )
        movements_detail = []
        for m in movements:
            movements_detail.append(
                {
                    "id": str(m.id),
                    "type": m.movement_type.value,
                    "amount": Decimal(str(m.amount)),
                    "balance_before": Decimal(str(m.balance_before)),
                    "balance_after": Decimal(str(m.balance_after)),
                    "description": m.description or "",
                    "reference_type": m.reference_type,
                    "reference_id": str(m.reference_id) if m.reference_id else None,
                    "cashier": m.user.username if m.user else "Desconocido",
                    "created_at": m.created_at,
                    "is_suspicious": ReportService._is_suspicious_movement(m),
                }
            )

        audit["orders"] = orders_detail
        audit["movements_detail"] = movements_detail
        return audit

    @staticmethod
    def get_daily_sales_summary(target_date: Optional[datetime.date] = None) -> dict:
        """
        Resumen de ventas de un día específico (por defecto hoy):
          - Total vendido
          - Desglose por método de pago
          - Número de órdenes
          - Cajeros que trabajaron
          - Alertas: sesiones aún abiertas
        """
        if target_date is None:
            target_date = datetime.date.today()

        start_dt = datetime.datetime.combine(target_date, datetime.time.min)
        end_dt = datetime.datetime.combine(target_date, datetime.time.max)

        paid_orders = (
            db.session.query(Order)
            .filter(
                Order.status == OrderStatus.PAID,
                Order.closed_at >= start_dt,
                Order.closed_at <= end_dt,
            )
            .all()
        )

        totals_by_method: dict[str, Decimal] = {
            PaymentMethod.CASH.value: Decimal("0"),
            PaymentMethod.CARD.value: Decimal("0"),
            PaymentMethod.TRANSFER.value: Decimal("0"),
        }
        grand_total = Decimal("0")
        cashiers_ids: set[str] = set()

        for order in paid_orders:
            cashiers_ids.add(str(order.user_id))
            for p in order.payments:
                amt = Decimal(str(p.amount_paid))
                totals_by_method[p.method.value] = (
                    totals_by_method.get(p.method.value, Decimal("0")) + amt
                )
                grand_total += amt

        # Cajeros activos ese día
        cashiers = (
            (db.session.query(User).filter(User.id.in_(cashiers_ids)).all())
            if cashiers_ids
            else []
        )

        # Sesiones que siguen abiertas (posible olvido de cierre)
        open_sessions = (
            db.session.query(RegisterSession)
            .filter(
                RegisterSession.status == RegisterStatus.OPEN,
                RegisterSession.opened_at >= start_dt,
                RegisterSession.opened_at <= end_dt,
            )
            .all()
        )

        return {
            "date": target_date.isoformat(),
            "total_orders": len(paid_orders),
            "grand_total": grand_total.quantize(Decimal("0.01")),
            "totals_by_method": {
                k: v.quantize(Decimal("0.01")) for k, v in totals_by_method.items()
            },
            "cashiers": [{"id": str(u.id), "username": u.username} for u in cashiers],
            "open_sessions_count": len(open_sessions),
            "open_sessions_alert": len(open_sessions) > 0,
        }

    @staticmethod
    def get_suspicious_movements(
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
    ) -> List[dict]:
        """
        Retorna todos los movimientos de tipo WITHDRAWAL marcados como sospechosos:
          - Sin referencia de orden
          - Monto superior al umbral SUSPICIOUS_WITHDRAWAL_THRESHOLD
        Ordenados del más reciente al más antiguo.
        """
        query = db.session.query(CashMovement).filter(
            CashMovement.movement_type == MovementType.WITHDRAWAL
        )

        if start_date:
            query = query.filter(
                CashMovement.created_at
                >= datetime.datetime.combine(start_date, datetime.time.min)
            )
        if end_date:
            query = query.filter(
                CashMovement.created_at
                <= datetime.datetime.combine(end_date, datetime.time.max)
            )

        movements = query.order_by(CashMovement.created_at.desc()).all()

        return [
            {
                "id": str(m.id),
                "session_id": str(m.register_session_id),
                "cashier": m.user.username if m.user else "Desconocido",
                "amount": abs(Decimal(str(m.amount))),
                "balance_after": Decimal(str(m.balance_after)),
                "description": m.description or "",
                "created_at": m.created_at,
                "is_suspicious": ReportService._is_suspicious_movement(m),
            }
            for m in movements
            if ReportService._is_suspicious_movement(m)
        ]

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    @staticmethod
    def _build_session_audit(session: RegisterSession) -> dict:
        """
        Construye el dict de auditoría de una sesión de caja.
        Centraliza la lógica compartida entre get_register_audit_trail y
        get_session_detail.
        """
        opener: Optional[User] = (
            db.session.get(User, session.opened_by) if session.opened_by else None
        )
        closer: Optional[User] = (
            db.session.get(User, session.closed_by) if session.closed_by else None
        )

        # Totales de venta de la sesión
        sales_by_method: dict[str, Decimal] = {
            PaymentMethod.CASH.value: Decimal("0"),
            PaymentMethod.CARD.value: Decimal("0"),
            PaymentMethod.TRANSFER.value: Decimal("0"),
        }
        total_sales = Decimal("0")
        cancelled_count = 0

        orders = (
            db.session.query(Order)
            .filter(Order.register_session_id == str(session.id))
            .all()
        )
        for order in orders:
            if order.status == OrderStatus.CANCELLED:
                cancelled_count += 1
                continue
            for p in order.payments:
                amt = Decimal(str(p.amount_paid))
                sales_by_method[p.method.value] = (
                    sales_by_method.get(p.method.value, Decimal("0")) + amt
                )
                total_sales += amt

        # Retiros de la sesión
        withdrawals = (
            db.session.query(CashMovement)
            .filter(
                CashMovement.register_session_id == str(session.id),
                CashMovement.movement_type == MovementType.WITHDRAWAL,
            )
            .all()
        )
        total_withdrawals = sum(abs(Decimal(str(w.amount))) for w in withdrawals)
        suspicious_withdrawals = [
            w for w in withdrawals if ReportService._is_suspicious_movement(w)
        ]

        # Determinar estado del descuadre
        difference: Optional[Decimal] = (
            Decimal(str(session.difference)) if session.difference is not None else None
        )
        if difference is None:
            discrepancy_status = "open"
        elif difference == Decimal("0"):
            discrepancy_status = "ok"
        elif difference > Decimal("0"):
            discrepancy_status = "surplus"
        else:
            discrepancy_status = "deficit"

        # Duración de la sesión
        duration_minutes: Optional[int] = None
        if session.opened_at and session.closed_at:
            delta = session.closed_at - session.opened_at
            duration_minutes = int(delta.total_seconds() / 60)

        return {
            "id": str(session.id),
            "status": session.status.value,
            "opener": opener.username if opener else "Desconocido",
            "closer": closer.username if closer else None,
            "opened_at": session.opened_at,
            "closed_at": session.closed_at,
            "duration_minutes": duration_minutes,
            "opening_amount": Decimal(str(session.opening_amount)),
            "closing_amount": Decimal(str(session.closing_amount))
            if session.closing_amount
            else None,
            "expected_amount": Decimal(str(session.expected_amount))
            if session.expected_amount
            else None,
            "difference": difference,
            "discrepancy_status": discrepancy_status,
            "total_sales": total_sales.quantize(Decimal("0.01")),
            "sales_by_method": {
                k: v.quantize(Decimal("0.01")) for k, v in sales_by_method.items()
            },
            "total_orders": len([o for o in orders if o.status == OrderStatus.PAID]),
            "cancelled_orders": cancelled_count,
            "total_withdrawals": total_withdrawals.quantize(Decimal("0.01")),
            "suspicious_withdrawal_count": len(suspicious_withdrawals),
            "has_alerts": len(suspicious_withdrawals) > 0
            or discrepancy_status == "deficit",
        }

    @staticmethod
    def _is_suspicious_movement(movement: CashMovement) -> bool:
        """
        Un retiro es sospechoso si:
          1. El monto absoluto supera el umbral configurado, O
          2. No tiene referencia de orden ni descripción.
        """
        if movement.movement_type != MovementType.WITHDRAWAL:
            return False
        amount = abs(Decimal(str(movement.amount)))
        over_threshold = amount >= SUSPICIOUS_WITHDRAWAL_THRESHOLD
        no_justification = not movement.description and movement.reference_type not in (
            "order",
            "adjustment",
        )
        return over_threshold or no_justification
