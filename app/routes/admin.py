from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.utils.decorators import admin_required
from app.services.product_service import ProductService
from app.services.user_service import UserService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')

# --- Gestión de Productos (CRUD) ---
@admin_bp.route('/products')
@login_required
@admin_required
def products():
    try:
        products_list = ProductService.get_all_products(is_active=True)
        return render_template('admin/products.html', products=products_list)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/products/new', methods=['GET'])
@login_required
@admin_required
def new_product():
    return render_template('admin/product_form.html')

@admin_bp.route('/products', methods=['POST'])
@login_required
@admin_required
def create_product():
    try:
        data = request.form.to_dict()
        # Se asume que el servicio y la base de datos manejan la conversión de tipos,
        # pero pasamos los valores base como llegan o preprocesados si es necesario.
        ProductService.create_product(data)
        flash('Producto creado exitosamente.', 'success')
        return redirect(url_for('admin.products'))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.new_product'))

@admin_bp.route('/products/<id>/edit', methods=['GET'])
@login_required
@admin_required
def edit_product(id):
    try:
        product = ProductService.get_product_by_id(id)
        if not product:
            flash('Producto no encontrado.', 'danger')
            return redirect(url_for('admin.products'))
        return render_template('admin/product_form.html', product=product)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.products'))

@admin_bp.route('/products/<id>/update', methods=['POST'])
@login_required
@admin_required
def update_product(id):
    try:
        data = request.form.to_dict()
        ProductService.update_product(id, data)
        flash('Producto actualizado exitosamente.', 'success')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('admin.products'))

@admin_bp.route('/products/<id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    try:
        ProductService.delete_product(id)
        flash('Producto eliminado exitosamente.', 'success')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('admin.products'))

# --- Importación Masiva de Productos ---
@admin_bp.route('/products/import', methods=['GET'])
@login_required
@admin_required
def import_products_form():
    return render_template('admin/product_import.html')

@admin_bp.route('/products/import', methods=['POST'])
@login_required
@admin_required
def import_products():
    try:
        # TODO: Implementar llamada a ImportService
        flash('Función de importación pendiente de implementación.', 'info')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('admin.products'))

# --- Gestión de Usuarios (CRUD) ---
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    try:
        users_list = UserService.get_all_users()
        return render_template('admin/users.html', users=users_list)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/users/new', methods=['GET'])
@login_required
@admin_required
def new_user():
    return render_template('admin/user_form.html')

@admin_bp.route('/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    try:
        data = request.form.to_dict()
        UserService.create_user(data)
        flash('Usuario creado exitosamente.', 'success')
        return redirect(url_for('admin.users'))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.new_user'))

@admin_bp.route('/users/<id>/edit', methods=['GET'])
@login_required
@admin_required
def edit_user(id):
    try:
        user = UserService.get_user_by_id(id)
        if not user:
            flash('Usuario no encontrado.', 'danger')
            return redirect(url_for('admin.users'))
        return render_template('admin/user_form.html', user=user)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.users'))

@admin_bp.route('/users/<id>/update', methods=['POST'])
@login_required
@admin_required
def update_user(id):
    try:
        data = request.form.to_dict()
        UserService.update_user(id, data)
        flash('Usuario actualizado exitosamente.', 'success')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<id>/deactivate', methods=['POST'])
@login_required
@admin_required
def deactivate_user(id):
    try:
        UserService.delete_user(id)
        flash('Usuario desactivado exitosamente.', 'success')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('admin.users'))