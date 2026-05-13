from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app.utils.decorators import admin_required
from app.services.product_service import ProductService
from app.services.user_service import UserService
from app.services.import_service import ImportService
from app.services.report_service import ReportService
from app.models.domain import Category, GenericStatus, Order, OrderStatus, Table
from app.extensions import db
import datetime
import io

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ─── Dashboard Analítico ─────────────────────────────────────────────────────
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    try:
        today = datetime.date.today()

        # ── Filtros de fecha (GET params) ────────────────────────────────
        try:
            start_date = datetime.date.fromisoformat(request.args.get('start_date', ''))
        except ValueError:
            start_date = today - datetime.timedelta(days=7)

        try:
            end_date = datetime.date.fromisoformat(request.args.get('end_date', ''))
        except ValueError:
            end_date = today

        # Caja(s) abiertas GLOBALES (sin importar fecha — para la alerta)
        open_sessions_total = ReportService.count_open_sessions()

        daily       = ReportService.get_daily_sales_summary(start_date=start_date, end_date=end_date)
        audit_trail = ReportService.get_register_audit_trail(
            start_date=start_date,
            end_date=end_date,
        )
        suspicious  = ReportService.get_suspicious_movements(
            start_date=start_date,
            end_date=end_date,
        )
        suspicious_count = len(suspicious)

        return render_template(
            'admin/dashboard.html',
            daily=daily,
            audit_trail=audit_trail,
            suspicious=suspicious,
            suspicious_count=suspicious_count,
            today=today,
            start_date=start_date,
            end_date=end_date,
            open_sessions_total=open_sessions_total,
        )
    except Exception as e:
        flash(f'Error al cargar el dashboard: {str(e)}', 'danger')
        return render_template(
            'admin/dashboard.html',
            daily=None, audit_trail=[], suspicious=[], suspicious_count=0,
            today=datetime.date.today(),
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today(),
            open_sessions_total=0,
        )


# ─── Gestión de Productos (CRUD) ─────────────────────────────────────────────
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


# ─── Descarga de Catálogo actual (UPSERT-ready) ───────────────────────────────
@admin_bp.route('/products/export-catalog')
@login_required
@admin_required
def export_catalog():
    """Descarga todos los productos activos como CSV listo para edición masiva."""
    try:
        csv_bytes = ImportService.export_catalog_csv()
        buf = io.BytesIO(csv_bytes)
        buf.seek(0)
        filename = f"catalogo_{datetime.date.today().isoformat()}.csv"
        return send_file(buf, mimetype='text/csv; charset=utf-8',
                         as_attachment=True, download_name=filename)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.products'))


# ─── Plantilla CSV vacía ──────────────────────────────────────────────────────
@admin_bp.route('/products/download-template')
@login_required
@admin_required
def download_csv_template():
    """Descarga una plantilla CSV vacía con las cabeceras requeridas + BOM."""
    header  = 'sku,nombre,categoria,precio,stock,descripcion,image_url,precio_costo,stock_minimo,status\n'
    example = 'CAF-001,Café Americano,Bebidas Calientes,5000,50,Café negro sin leche,,3000,10,active\n'
    content = '\ufeff' + header + example

    buf = io.BytesIO(content.encode('utf-8'))
    buf.seek(0)
    return send_file(buf, mimetype='text/csv; charset=utf-8',
                     as_attachment=True, download_name='plantilla_productos.csv')


# ─── Importación Masiva ───────────────────────────────────────────────────────
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

        msg = f"{result['imported']} producto(s) creado(s). {result['updated']} actualizado(s)."
        if result['skipped']:
            msg += f" {result['skipped']} fila(s) rechazada(s)."

        flash(msg, 'success' if (result['imported'] + result['updated']) > 0 else 'warning')
        return render_template('admin/product_import.html', import_result=result)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.import_products_form'))
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.import_products_form'))


# ─── CRUD de Mesas ────────────────────────────────────────────────────────────
@admin_bp.route('/tables')
@login_required
@admin_required
def tables():
    try:
        tables_list = db.session.query(Table).order_by(Table.name).all()
        return render_template('admin/tables.html', tables=tables_list)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/tables/new', methods=['GET'])
@login_required
@admin_required
def new_table():
    return render_template('admin/table_form.html', table=None)


@admin_bp.route('/tables', methods=['POST'])
@login_required
@admin_required
def create_table():
    try:
        name     = request.form.get('name', '').strip()
        capacity = int(request.form.get('capacity', 2))
        if not name:
            raise ValueError("El nombre de la mesa no puede estar vacío.")
        # Verificar nombre único
        existing = db.session.query(Table).filter_by(name=name).first()
        if existing:
            raise ValueError(f"Ya existe una mesa con el nombre '{name}'.")
        table = Table(name=name, capacity=capacity, status=GenericStatus.ACTIVE)
        db.session.add(table)
        db.session.commit()
        flash(f"Mesa '{name}' creada exitosamente.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('admin.tables'))


@admin_bp.route('/tables/<id>/edit', methods=['GET'])
@login_required
@admin_required
def edit_table(id):
    try:
        table = db.session.get(Table, id)
        if not table:
            flash('Mesa no encontrada.', 'danger')
            return redirect(url_for('admin.tables'))
        return render_template('admin/table_form.html', table=table)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.tables'))


@admin_bp.route('/tables/<id>/update', methods=['POST'])
@login_required
@admin_required
def update_table(id):
    try:
        table = db.session.get(Table, id)
        if not table:
            flash('Mesa no encontrada.', 'danger')
            return redirect(url_for('admin.tables'))
        name     = request.form.get('name', '').strip()
        capacity = int(request.form.get('capacity', table.capacity or 2))
        if not name:
            raise ValueError("El nombre no puede estar vacío.")
        # Comprobar unicidad excluyendo la mesa actual
        clash = db.session.query(Table).filter(
            Table.name == name, Table.id != table.id
        ).first()
        if clash:
            raise ValueError(f"Ya existe otra mesa con el nombre '{name}'.")
        table.name     = name
        table.capacity = capacity
        db.session.commit()
        flash(f"Mesa '{name}' actualizada.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('admin.tables'))


@admin_bp.route('/tables/<id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_table(id):
    try:
        table = db.session.get(Table, id)
        if not table:
            flash('Mesa no encontrada.', 'danger')
            return redirect(url_for('admin.tables'))

        # Bloquear si tiene órdenes OPEN
        open_orders = db.session.query(Order).filter(
            Order.table_id == table.id,
            Order.status == OrderStatus.OPEN,
        ).count()
        if open_orders:
            raise ValueError(
                f"La mesa '{table.name}' tiene {open_orders} orden(es) abierta(s). "
                "Ciérralas antes de eliminar la mesa."
            )

        # Borrado lógico (desactivar)
        table.status = GenericStatus.INACTIVE
        db.session.commit()
        flash(f"Mesa '{table.name}' desactivada.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('admin.tables'))


# ─── Gestión de Usuarios (CRUD) ───────────────────────────────────────────────
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
        if str(current_user.id) == str(id):
            flash('No puedes desactivar tu propia cuenta.', 'warning')
            return redirect(url_for('admin.users'))
        UserService.delete_user(id)
        flash('Usuario desactivado exitosamente.', 'success')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('admin.users'))