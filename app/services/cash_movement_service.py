from app.extensions import db
from app.models.domain import CashMovement, RegisterSession, MovementType, RegisterStatus
from sqlalchemy.exc import SQLAlchemyError

class CashMovementService:
    @staticmethod
    def _get_current_balance(session_id: str) -> float:
        last_movement = db.session.query(CashMovement)\
            .filter_by(register_session_id=session_id)\
            .order_by(CashMovement.created_at.desc())\
            .first()
        return float(last_movement.balance_after) if last_movement else 0.0

    @staticmethod
    def _validate_session_open(session_id: str) -> RegisterSession:
        session = db.session.get(RegisterSession, session_id)
        if not session:
            raise ValueError("La sesión de caja no existe.")
        if session.status == RegisterStatus.CLOSED:
            raise ValueError("No se pueden registrar movimientos en una sesión cerrada.")
        return session

    @staticmethod
    def _execute_movement(session_id: str, user_id: str, amount: float, movement_type: MovementType, description: str = None):
        CashMovementService._validate_session_open(session_id)
        
        balance_before = CashMovementService._get_current_balance(session_id)
        balance_after = balance_before + amount

        movement = CashMovement(
            register_session_id=session_id,
            user_id=user_id,
            movement_type=movement_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description
        )
        
        try:
            db.session.add(movement)
            db.session.commit()
            return movement
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error transaccional al registrar movimiento: {str(e)}")

    @staticmethod
    def record_opening(session_id: str, user_id: str, amount: float):
        return CashMovementService._execute_movement(session_id, user_id, amount, MovementType.OPENING, "Apertura de caja")

    @staticmethod
    def record_closing(session_id: str, user_id: str, amount: float, expected: float):
        difference = amount - expected
        description = f"Cierre de caja. Efectivo real: {amount} | Esperado: {expected} | Diferencia: {difference}"
        return CashMovementService._execute_movement(session_id, user_id, amount, MovementType.CLOSING, description)

    @staticmethod
    def record_withdrawal(session_id: str, user_id: str, amount: float, description: str):
        if amount <= 0:
            raise ValueError("El monto de retiro debe ser un valor positivo.")
        return CashMovementService._execute_movement(session_id, user_id, -amount, MovementType.WITHDRAWAL, description)

    @staticmethod
    def record_deposit(session_id: str, user_id: str, amount: float, description: str):
        if amount <= 0:
            raise ValueError("El monto de depósito debe ser un valor positivo.")
        return CashMovementService._execute_movement(session_id, user_id, amount, MovementType.DEPOSIT, description)

    @staticmethod
    def record_adjustment(session_id: str, user_id: str, amount: float, description: str):
        return CashMovementService._execute_movement(session_id, user_id, amount, MovementType.ADJUSTMENT, description)

    @staticmethod
    def get_session_movements(session_id: str):
        return db.session.query(CashMovement)\
            .filter_by(register_session_id=session_id)\
            .order_by(CashMovement.created_at.asc())\
            .all()

    @staticmethod
    def get_cashier_movements(user_id: str, start_date, end_date):
        return db.session.query(CashMovement)\
            .filter(
                CashMovement.user_id == user_id,
                CashMovement.created_at >= start_date,
                CashMovement.created_at <= end_date
            ).order_by(CashMovement.created_at.asc()).all()

    @staticmethod
    def get_all_movements(start_date, end_date):
        return db.session.query(CashMovement)\
            .filter(
                CashMovement.created_at >= start_date,
                CashMovement.created_at <= end_date
            ).order_by(CashMovement.created_at.desc()).all()