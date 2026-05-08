from functools import wraps
from flask import redirect, flash, abort
from flask_login import current_user
from app.models.domain import UserRole

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def cashier_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # El admin también puede operar como cajero
        if not current_user.is_authenticated or current_user.role not in [UserRole.CASHIER, UserRole.ADMIN]:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function