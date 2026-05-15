import decimal

from app.extensions import db
from app.models.domain import CashMovement, RegisterSession, MovementType, RegisterStatus
from sqlalchemy.exc import SQLAlchemyError


class CashMovementService:
    """Único punto de escritura para movimientos de caja. Mantiene un saldo corrido por sesión."""

    @staticmethod
    def _get_current_balance(session_id: str) -> decimal.Decimal:
        """Retorna el balance_after del último movimiento de la sesión, o 0 si no hay ninguno."""
        last_movement = db.session.query(CashMovement)\
            .filter_by(register_session_id=session_id)\
            .order_by(CashMovement.created_at.desc())\
            .first()
        return decimal.Decimal(str(last_movement.balance_after)) if last_movement else decimal.Decimal("0")

    @staticmethod
    def _validate_session_open(session_id: str) -> RegisterSession:
        """Lanza ValueError si la sesión no existe o ya está cerrada."""
        session = db.session.get(RegisterSession, session_id)
        if not session:
            raise ValueError("La sesión de caja no existe.")
        if session.status == RegisterStatus.CLOSED:
            raise ValueError("No se pueden registrar movimientos en una sesión cerrada.")
        return session

    @staticmethod
    def _execute_movement(
        session_id: str,
        user_id: str,
        amount: decimal.Decimal,
        movement_type: MovementType,
        description: str = None,
    ):
        """
        Crea un CashMovement calculando balance_before y balance_after.
        Todos los métodos públicos pasan por aquí — es la única función que escribe en la tabla.
        Los retiros se pasan con amount negativo desde record_withdrawal.
        """
        CashMovementService._validate_session_open(session_id)

        amount = decimal.Decimal(str(amount))
        balance_before = CashMovementService._get_current_balance(session_id)
        balance_after = balance_before + amount

        movement = CashMovement(
            register_session_id=session_id,
            user_id=user_id,
            movement_type=movement_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
        )

        try:
            db.session.add(movement)
            db.session.commit()
            return movement
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error transaccional al registrar movimiento: {str(e)}")

    @staticmethod
    def record_opening(session_id: str, user_id: str, amount: decimal.Decimal):
        """Registra el efectivo inicial al abrir la caja."""
        return CashMovementService._execute_movement(
            session_id, user_id, amount, MovementType.OPENING, "Apertura de caja"
        )

    @staticmethod
    def record_closing(
        session_id: str, user_id: str,
        amount: decimal.Decimal, expected: decimal.Decimal,
    ):
        """Registra el cierre de caja con diferencia entre efectivo real y esperado."""
        amount   = decimal.Decimal(str(amount))
        expected = decimal.Decimal(str(expected))
        difference = amount - expected
        description = (
            f"Cierre de caja. Efectivo real: {amount} | "
            f"Esperado: {expected} | Diferencia: {difference}"
        )
        return CashMovementService._execute_movement(
            session_id, user_id, amount, MovementType.CLOSING, description
        )

    @staticmethod
    def record_withdrawal(
        session_id: str, user_id: str,
        amount: decimal.Decimal, description: str,
    ):
        """Registra un retiro manual. El amount se invierte a negativo internamente."""
        amount = decimal.Decimal(str(amount))
        if amount <= decimal.Decimal("0"):
            raise ValueError("El monto de retiro debe ser un valor positivo.")
        return CashMovementService._execute_movement(
            session_id, user_id, -amount, MovementType.WITHDRAWAL, description
        )

    @staticmethod
    def record_deposit(
        session_id: str, user_id: str,
        amount: decimal.Decimal, description: str,
    ):
        """Registra un depósito manual o el ingreso de efectivo de una venta."""
        amount = decimal.Decimal(str(amount))
        if amount <= decimal.Decimal("0"):
            raise ValueError("El monto de depósito debe ser un valor positivo.")
        return CashMovementService._execute_movement(
            session_id, user_id, amount, MovementType.DEPOSIT, description
        )

    @staticmethod
    def record_adjustment(
        session_id: str, user_id: str,
        amount: decimal.Decimal, description: str,
    ):
        """Registra un ajuste de discrepancia (puede ser positivo o negativo)."""
        return CashMovementService._execute_movement(
            session_id, user_id, amount, MovementType.ADJUSTMENT, description
        )

    @staticmethod
    def get_session_movements(session_id: str):
        """Retorna todos los movimientos de una sesión ordenados cronológicamente."""
        return db.session.query(CashMovement)\
            .filter_by(register_session_id=session_id)\
            .order_by(CashMovement.created_at.asc())\
            .all()

    @staticmethod
    def get_cashier_movements(user_id: str, start_date, end_date):
        """Retorna movimientos de un cajero específico en un rango de fechas."""
        return db.session.query(CashMovement)\
            .filter(
                CashMovement.user_id == user_id,
                CashMovement.created_at >= start_date,
                CashMovement.created_at <= end_date
            ).order_by(CashMovement.created_at.asc()).all()

    @staticmethod
    def get_all_movements(start_date, end_date):
        """Retorna todos los movimientos del sistema en un rango de fechas (para auditoría)."""
        return db.session.query(CashMovement)\
            .filter(
                CashMovement.created_at >= start_date,
                CashMovement.created_at <= end_date
            ).order_by(CashMovement.created_at.desc()).all()