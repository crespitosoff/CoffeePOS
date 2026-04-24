from app.extensions import db
import uuid, enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as Uuid, ENUM

# Definir Enums
class UserRole(enum.Enum):
    admin = 'admin'
    manager = 'manager'
    cashier = 'cashier'

class UserStatus(enum.Enum):
    active = 'active'
    inactive = 'inactive'
    suspended = 'suspended'
    terminated = 'terminated'

class GenericStatus(enum.Enum):
    active = 'active'
    inactive = 'inactive'
    archived = 'archived'

# 2. Definimos la clase (Modelo)
class User(db.Model):
    __tablename__ = "users" # Nombre de la tabla en la BD

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(120), unique=True)

    role: Mapped[UserRole] = mapped_column(
        ENUM(UserRole, name="user_role",
        create_type=False)
    )
    status: Mapped[UserStatus] = mapped_column(
        ENUM(UserStatus, name="user_status", create_type=False),
        default="active"
    )

    #   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

class Category(db.Model):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)

    status: Mapped[GenericStatus] = mapped_column(
        ENUM(GenericStatus, name="generic_status", create_type=False),
        default="active"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )


    # Relación uno a muchos (una categoría tiene muchos productos)
    products: Mapped[List["Product"]] = relationship(back_populates="category")

class Product(db.Model):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sku: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(255))

    price: Mapped[float] = mapped_column()
    unit_cost: Mapped[float] = mapped_column()

    stock: Mapped[int] = mapped_column(default=0)
    min_stock: Mapped[int] = mapped_column(default=0)

    image_url: Mapped[Optional[str]] = mapped_column(String(255))

    status: Mapped[GenericStatus] = mapped_column(
        ENUM(GenericStatus, name="generic_status", create_type=False),
        default="active"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relación muchos a uno (un producto pertenece a una categoría)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"))
    category: Mapped["Category"] = relationship(back_populates="products")
