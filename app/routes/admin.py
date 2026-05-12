from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.utils.decorators import admin_required
from app.services.product_service import ProductService
from app.services.user_service import UserService
from app.services.import_service import ImportService
from app.services.report_service import ReportService
from app.models.domain import Category, GenericStatus
from app.extensions import db
import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# --- Dashboard Analítico (Panel Antirrobo) ---
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    try:
        today        = datetime.date.today()
        daily        = ReportService.get_daily_sales_summary(today)
        audit_trail  = ReportService.get_register_audit_trail(
            start_date=today - datetime.timedelta(days=7),
            end_date=today,
        )
        suspicious   = ReportService.get_suspicious_movements(
            start_date=today - datetime.timedelta(days=7),
            end_date=today,
        )
        return render_template(
            'admin/dashboard.html',
            daily=daily,
            audit_trail=audit_trail,
            suspicious=suspicious,
            today=today,
        )
    except Exception as e:
        flash(f'Error al cargar el dashboard: {str(e)}', 'danger')
        return render_template(
            'admin/dashboard.html',
            daily=None, audit_trail=[], suspicious=[], today=datetime.date.today()
        )


# --- Gestión de Productos (CRUD) ---
@admin_bp.route('/products')
@login_required
@admin_required
def products():
    try:
        products_list = ProductService.get_all_products(is_active=False)
        return render_template('admin/products.html', products=products_list)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/products/new', methods=['GET'])
@login_required
@admin_required
def new_product():
    categories = db.session.query(Category).filter(
        Category.status == GenericStatus.ACTIVE
    ).order_by(Category.name).all()
    return render_template('admin/product_form.html', product=None, categories=categories)


@admin_bp.route('/products', methods=['POST'])
@login_required
@admin_required
def create_product():
    try:
        data = request.form.to_dict()
        # Normalizar category_id vacío a None
        if not data.get('category_id'):
            data['category_id'] = None
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
        categories = db.session.query(Category).filter(
            Category.status == GenericStatus.ACTIVE
        ).order_by(Category.name).all()
        return render_template('admin/product_form.html', product=product, categories=categories)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.products'))


@admin_bp.route('/products/<id>/update', methods=['POST'])
@login_required
@admin_required
def update_product(id):
    try:
        data = request.form.to_dict()
        if not data.get('category_id'):
            data['category_id'] = None
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
        flash('Producto archivado exitosamente.', 'success')
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
        csv_file = request.files.get('csv_file')
        if not csv_file or csv_file.filename == '':
            flash('Debes seleccionar un archivo CSV.', 'warning')
            return redirect(url_for('admin.import_products_form'))

        if not csv_file.filename.lower().endswith('.csv'):
            flash('El archivo debe tener extensión .csv', 'warning')
            return redirect(url_for('admin.import_products_form'))

        result = ImportService.process_csv(csv_file.stream)

        # Construir mensaje de resumen
        msg = f"{result['imported']} producto(s) importado(s)."
        if result['skipped']:
            msg += f" {result['skipped']} fila(s) ignorada(s) por errores."

        category = 'success' if result['imported'] > 0 else 'warning'
        flash(msg, category)

        return render_template(
            'admin/product_import.html',
            import_result=result,
        )
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.import_products_form'))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.import_products_form'))


# --- Gestión de Usuarios (CRUD) ---
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    try:
        users_list = UserService.get_all_users(active_only=False)
        return render_template('admin/users.html', users=users_list)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/users/new', methods=['GET'])
@login_required
@admin_required
def new_user():
    return render_template('admin/user_form.html', user=None)


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
        # Evitar que el admin se desactive a sí mismo
        if str(current_user.id) == str(id):
            flash('No puedes desactivar tu propia cuenta.', 'warning')
            return redirect(url_for('admin.users'))
        UserService.delete_user(id)
        flash('Usuario desactivado exitosamente.', 'success')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('admin.users'))