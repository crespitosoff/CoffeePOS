# Base de Datos — CoffeePOS

## Motor y Configuración

- **Motor:** PostgreSQL
- **ORM:** SQLAlchemy 2.0
- **Migraciones:** (vía Flask-Migrate)
- **Conexión:** variable `DATABASE_URL` en `.env`

---

## Diagrama de Entidades

```
StoreSetting        Category
                       │
                    Product ──────────────────┐
                                              │
User ──┬── RegisterSession ──── Order ────── OrderItem
       │         │                │
       │         │             Payment
       │         │
       └── CashMovement
                         Table ──── Order
```

---

## Modelos

### `Category`
Agrupa productos por tipo (ej. bebidas, postres,etc).

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID PK | gen_random_uuid() |
| name | VARCHAR(100) | unique |
| slug | VARCHAR(100) | unique, URL-friendly |
| description | TEXT | nullable |
| status | Enum(GenericStatus) | active / inactive / archived |

---

### `StoreSetting`
Configuración global del negocio. Solo debe existir **un registro**.

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID PK | |
| business_name | VARCHAR(200) | |
| tax_percentage | NUMERIC(5,2) | IVA por defecto 19% |
| currency | VARCHAR(10) | ej. COP |
| timezone | VARCHAR(50) | ej. America/Bogota |
| invoice_prefix | VARCHAR(20) | prefijo de recibos |

---

### `Table`
Mesas del local. Las órdenes de salón se asocian a una mesa.

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR(50) | unique |
| capacity | INTEGER | |
| status | Enum(GenericStatus) | |

---

### `User`
Empleados del sistema (admin o cajero).

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID PK | |
| username | VARCHAR(80) | unique |
| password_hash | VARCHAR(255) | bcrypt |
| full_name | VARCHAR(150) | |
| role | Enum(UserRole) | admin / cashier |
| status | Enum(UserStatus) | active / inactive / suspended / terminated |

---

### `Product`
Artículos del menú.

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID PK | |
| sku | VARCHAR(50) | unique |
| name | VARCHAR(150) | |
| description | TEXT | nullable |
| price | NUMERIC(10,2) | CHECK >= 0 |
| cost | NUMERIC(10,2) | CHECK >= 0, para margen |
| stock | INTEGER | inventario actual |
| min_stock | INTEGER | alerta de stock bajo |
| image_url | VARCHAR(500) | nullable |
| status | Enum(GenericStatus) | |
| category_id | UUID FK → Category | |

**Índices:** `(name)`, `(status)`

---

### `RegisterSession`
Sesión de caja (turno de un cajero).

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID PK | |
| opened_by | UUID FK → User | |
| closed_by | UUID FK → User | nullable |
| status | Enum(RegisterStatus) | open / closed |
| opening_amount | NUMERIC(10,2) | efectivo inicial |
| closing_amount | NUMERIC(10,2) | efectivo final reportado |
| difference | NUMERIC(10,2) | real vs esperado |
| opened_at | TIMESTAMP | |
| closed_at | TIMESTAMP | nullable |

**Restricción:** índice único parcial — solo puede haber **una sesión OPEN por usuario** a la vez.

---

### `Order`
Orden de un cliente (mesa o para llevar).

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID PK | |
| register_session_id | UUID FK → RegisterSession | |
| user_id | UUID FK → User | cajero que la creó |
| table_id | UUID FK → Table | nullable (para llevar) |
| status | Enum(OrderStatus) | open / preparing / ready / paid / cancelled |
| subtotal | NUMERIC(10,2) | |
| tax_amount | NUMERIC(10,2) | |
| total | NUMERIC(10,2) | |
| notes | TEXT | nullable |
| created_at | TIMESTAMP | |

**Índices:** `(created_at)`, `(status)`

---

### `OrderItem`
Línea de producto dentro de una orden.

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID PK | |
| order_id | UUID FK → Order | CASCADE DELETE |
| product_id | UUID FK → Product | |
| quantity | INTEGER | CHECK > 0 |
| base_price | NUMERIC(10,2) | precio al momento de venta |
| historical_cost | NUMERIC(10,2) | costo al momento de venta |
| subtotal | NUMERIC(10,2) | quantity × base_price |

> `base_price` e `historical_cost` se guardan en el momento de la venta para que los reportes sean precisos aunque el precio del producto cambie después.

---

### `Payment`
Registro del pago de una orden.

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID PK | |
| order_id | UUID FK → Order | |
| register_session_id | UUID FK → RegisterSession | |
| method | Enum(PaymentMethod) | cash / card / transfer |
| amount_paid | NUMERIC(10,2) | CHECK > 0 |
| change_amount | NUMERIC(10,2) | vuelto (solo efectivo) |
| reference | VARCHAR(100) | nullable (nro. transacción) |
| paid_at | TIMESTAMP | |

---

### `CashMovement`
Cada entrada o salida de efectivo en una sesión de caja.

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID PK | |
| register_session_id | UUID FK → RegisterSession | |
| user_id | UUID FK → User | quien registró el movimiento |
| type | Enum(MovementType) | opening / closing / withdrawal / deposit / adjustment |
| amount | NUMERIC(10,2) | positivo o negativo según tipo |
| balance_before | NUMERIC(10,2) | saldo antes del movimiento |
| balance_after | NUMERIC(10,2) | saldo después del movimiento |
| description | TEXT | nullable |
| created_at | TIMESTAMP | |

**Índices:** `(register_session_id)`, `(created_at)`

---

## Enums

| Enum | Valores |
|---|---|
| `GenericStatus` | active, inactive, archived |
| `MovementType` | opening, closing, withdrawal, deposit, adjustment |
| `OrderStatus` | open, preparing, ready, paid, cancelled |
| `PaymentMethod` | cash, card, transfer |
| `RegisterStatus` | open, closed |
| `UserRole` | admin, cashier |
| `UserStatus` | active, inactive, suspended, terminated |

---

## Comandos de Migración

```bash
# Crear nueva migración tras modificar modelos
flask db migrate -m "descripcion del cambio"

# Aplicar migraciones pendientes
flask db upgrade

# Revertir última migración
flask db downgrade
```
