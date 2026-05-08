from app.extensions import db
from typing import Optional
import datetime
import decimal
import enum
import uuid

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, PrimaryKeyConstraint, String, Table, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

class GenericStatus(str, enum.Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    ARCHIVED = 'archived'


class MovementType(str, enum.Enum):
    INCOME = 'income'
    EXPENSE = 'expense'


class OrderStatus(str, enum.Enum):
    OPEN = 'open'
    PREPARING = 'preparing'
    READY = 'ready'
    PAID = 'paid'
    CANCELLED = 'cancelled'


class PaymentMethod(str, enum.Enum):
    CASH = 'cash'
    CARD = 'card'
    TRANSFER = 'transfer'


class RegisterStatus(str, enum.Enum):
    OPEN = 'open'
    CLOSED = 'closed'


class UserRole(str, enum.Enum):
    ADMIN = 'admin'
    MANAGER = 'manager'
    CASHIER = 'cashier'
    BARISTA = 'barista'


class UserStatus(str, enum.Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'
    TERMINATED = 'terminated'


class Category(db.Model):
    __tablename__ = 'categories'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='categories_pkey'),
        UniqueConstraint('slug', name='categories_slug_key')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[Optional[GenericStatus]] = mapped_column(Enum(GenericStatus, values_callable=lambda cls: [member.value for member in cls], name='generic_status'), server_default=text("'active'::generic_status"))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))

    products: Mapped[list['Product']] = relationship('Product', back_populates='category')


class StoreSetting(db.Model):
    __tablename__ = 'store_settings'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='store_settings_pkey'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    business_name: Mapped[str] = mapped_column(String(150), nullable=False)
    commercial_name: Mapped[Optional[str]] = mapped_column(String(150))
    tax_id: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(String(30))    
    email: Mapped[Optional[str]] = mapped_column(String(120))
    website: Mapped[Optional[str]] = mapped_column(String(150))
    currency: Mapped[Optional[str]] = mapped_column(String(10), server_default=text("'COP'::character varying"))
    language: Mapped[Optional[str]] = mapped_column(String(10), server_default=text("'es-CO'::character varying"))
    timezone: Mapped[Optional[str]] = mapped_column(String(60), server_default=text("'America/Bogota'::character varying"))
    country_code: Mapped[Optional[str]] = mapped_column(String(5), server_default=text("'CO'::character varying"))
    tax_percentage: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 2), server_default=text('19.00'))
    invoice_prefix: Mapped[Optional[str]] = mapped_column(String(20), server_default=text("'FAC'::character varying"))
    next_invoice_number: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('1'))
    receipt_footer: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))


class Table(db.Model):
    __tablename__ = 'tables'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='tables_pkey'),
        UniqueConstraint('name', name='tables_name_key'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('2'))
    status: Mapped[Optional[GenericStatus]] = mapped_column(Enum(GenericStatus, values_callable=lambda cls: [member.value for member in cls], name='generic_status'), server_default=text("'active'::generic_status"))

    orders: Mapped[list['Order']] = relationship('Order', back_populates='table')


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='users_pkey'),
        UniqueConstraint('username', name='users_username_key')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, values_callable=lambda cls: [member.value for member in cls], name='user_role'), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(80))
    last_name: Mapped[Optional[str]] = mapped_column(String(80))
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    email: Mapped[Optional[str]] = mapped_column(String(120))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[Optional[UserStatus]] = mapped_column(Enum(UserStatus, values_callable=lambda cls: [member.value for member in cls], name='user_status'), server_default=text("'active'::user_status"))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))

    register_sessions_closed_by: Mapped[list['RegisterSession']] = relationship('RegisterSession', foreign_keys='[RegisterSession.closed_by]', back_populates='user')
    register_sessions_opened_by: Mapped[list['RegisterSession']] = relationship('RegisterSession', foreign_keys='[RegisterSession.opened_by]', back_populates='user_')
    orders: Mapped[list['Order']] = relationship('Order', back_populates='user')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    __tablename__ = 'products'
    __table_args__ = (
        CheckConstraint('price >= 0::numeric', name='products_price_check'),
        CheckConstraint('unit_cost >= 0::numeric', name='products_unit_cost_check'),
        PrimaryKeyConstraint('id', name='products_pkey'),
        UniqueConstraint('sku', name='products_sku_key'),
        Index('idx_products_name', 'name'),
        Index('idx_products_status', 'status')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    price: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey('categories.id'))
    sku: Mapped[Optional[str]] = mapped_column(String(60))
    description: Mapped[Optional[str]] = mapped_column(Text)
    unit_cost: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(12, 2), server_default=text('0'))
    stock: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'))
    min_stock: Mapped[Optional[int]] = mapped_column(Integer, server_default=text('0'))
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Optional[GenericStatus]] = mapped_column(Enum(GenericStatus, values_callable=lambda cls: [member.value for member in cls], name='generic_status'), server_default=text("'active'::generic_status"))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))

    category: Mapped[Optional['Category']] = relationship('Category', back_populates='products')
    order_items: Mapped[list['OrderItem']] = relationship('OrderItem', back_populates='product')


class RegisterSession(db.Model):
    __tablename__ = 'register_sessions'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='register_sessions_pkey'),
        Index('idx_single_open_register', 'status', postgresql_where="(status = 'open'::register_status)", unique=True)
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    opening_amount: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    opened_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey('users.id'))
    closed_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey('users.id'))
    closing_amount: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(12, 2))
    expected_amount: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(12, 2))
    difference: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(12, 2))
    status: Mapped[Optional[RegisterStatus]] = mapped_column(Enum(RegisterStatus, values_callable=lambda cls: [member.value for member in cls], name='register_status'), server_default=text("'open'::register_status"))
    opened_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))
    closed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    user: Mapped[Optional['User']] = relationship('User', foreign_keys=[closed_by], back_populates='register_sessions_closed_by')
    user_: Mapped[Optional['User']] = relationship('User', foreign_keys=[opened_by], back_populates='register_sessions_opened_by')
    orders: Mapped[list['Order']] = relationship('Order', back_populates='register_session')
    payments: Mapped[list['Payment']] = relationship('Payment', back_populates='register_session')


class Order(db.Model):
    __tablename__ = 'orders'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='orders_pkey'),
        Index('idx_orders_created_at', 'created_at'),
        Index('idx_orders_status', 'status')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey('users.id'))
    register_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey('register_sessions.id'))
    table_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey('tables.id'), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(100))
    subtotal: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(12, 2), server_default=text('0'))
    tax: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(12, 2), server_default=text('0'))
    total: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(12, 2), server_default=text('0'))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Optional[OrderStatus]] = mapped_column(Enum(OrderStatus, values_callable=lambda cls: [member.value for member in cls], name='order_status'), server_default=text("'open'::order_status"))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))
    closed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    register_session: Mapped[Optional['RegisterSession']] = relationship('RegisterSession', back_populates='orders')
    table: Mapped[Optional['Table']] = relationship('Table', back_populates='orders')
    user: Mapped[Optional['User']] = relationship('User', back_populates='orders')
    order_items: Mapped[list['OrderItem']] = relationship('OrderItem', back_populates='order')
    payments: Mapped[list['Payment']] = relationship('Payment', back_populates='order')


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    __table_args__ = (
        CheckConstraint('quantity > 0', name='order_items_quantity_check'),
        PrimaryKeyConstraint('id', name='order_items_pkey')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    base_price: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey('orders.id', ondelete='CASCADE'))
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey('products.id'))
    historical_cost: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(12, 2), server_default=text('0'))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    order: Mapped[Optional['Order']] = relationship('Order', back_populates='order_items')
    product: Mapped[Optional['Product']] = relationship('Product', back_populates='order_items')


class Payment(db.Model):
    __tablename__ = 'payments'
    __table_args__ = (
        CheckConstraint('amount_paid > 0::numeric', name='payments_amount_paid_check'),
        PrimaryKeyConstraint('id', name='payments_pkey'),
        Index('idx_payments_order_id', 'order_id')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, values_callable=lambda cls: [member.value for member in cls], name='payment_method'), nullable=False)
    amount_paid: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey('orders.id'))
    register_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey('register_sessions.id'))
    reference: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))

    order: Mapped[Optional['Order']] = relationship('Order', back_populates='payments')
    register_session: Mapped[Optional['RegisterSession']] = relationship('RegisterSession', back_populates='payments')
