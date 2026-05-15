from functools import wraps
from flask import redirect, flash, abort, session
from flask_login import current_user
from app.models.domain import UserRole


def admin_required(f):
    """Decorador: solo permite acceso a usuarios con rol 'admin'. Retorna 403 en caso contrario."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or session.get('role') != UserRole.ADMIN.value:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def cashier_required(f):
    """Decorador: permite acceso a 'cashier' y 'admin'. Retorna 403 para cualquier otro rol."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or session.get('role') not in [UserRole.CASHIER.value, UserRole.ADMIN.value]:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function