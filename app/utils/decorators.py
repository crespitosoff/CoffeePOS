from functools import wraps
from flask import redirect, flash, abort, session
from flask_login import current_user
from app.models.domain import UserRole

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or session.get('role') != UserRole.ADMIN.value:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def cashier_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or session.get('role') not in [UserRole.CASHIER.value, UserRole.ADMIN.value]:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function