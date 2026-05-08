from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app.models.domain import User, UserRole
from app.extensions import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Validación: Interceptar y redirigir usuarios activos inmediatamente
    if current_user.is_authenticated:
        if current_user.role == UserRole.ADMIN:
            return redirect('/admin/dashboard')
        return redirect('/pos/dashboard')
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = db.session.query(User).filter(User.username == username).first()
        
        if user and user.check_password(password):
            login_user(user)
            if user.role == UserRole.ADMIN:
                return redirect('/admin/dashboard')
            else:
                return redirect('/pos/dashboard')
        else:
            flash("Credenciales inválidas")
            
    return render_template('auth/login.html')

@auth_bp.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))