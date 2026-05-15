# API y Rutas HTTP — CoffeePOS

## Convenciones

- Las rutas que renderizan HTML devuelven templates Jinja2.
- Las rutas prefijadas con `/api/` devuelven JSON.
- Protección por rol mediante decoradores `@admin_required` y `@cashier_required`.
- Todos los formularios usan `POST` con `application/x-www-form-urlencoded`.

---

## Blueprint: `auth` — Autenticación

### `GET /login`
Muestra el formulario de inicio de sesión.

### `POST /login`
Autentica al usuario.

**Form params:**
| Campo | Tipo | Descripción |
|---|---|---|
| username | string | nombre de usuario |
| password | string | contraseña |

**Respuesta exitosa:** redirige a `/admin/dashboard` (admin) o `/pos/dashboard` (cajero).  
**Error:** renderiza `login.html` con mensaje de error.

---

### `GET /logout`
Cierra la sesión y redirige a `/login`.

---

## Blueprint: `admin` — Panel de Administración

> Todas las rutas requieren `@admin_required`.

### Dashboard

#### `GET /admin/dashboard`
Panel principal con resumen de ventas, auditoría y movimientos sospechosos.

**Query params opcionales:**
| Param | Descripción |
|---|---|
| start_date | fecha inicio filtro (YYYY-MM-DD) |
| end_date | fecha fin filtro (YYYY-MM-DD) |

---

### Productos

#### `GET /admin/products`
Lista todos los productos.

#### `GET /admin/products/new`
Formulario de creación de producto.

#### `POST /admin/products/new`
Crea un nuevo producto.

**Form params:** `name`, `sku`, `price`, `cost`, `stock`, `min_stock`, `category_id`, `description`, `image_url`, `status`

#### `GET /admin/products/<id>/edit`
Formulario de edición de producto.

#### `POST /admin/products/<id>/edit`
Actualiza un producto existente. Mismos campos que creación.

#### `POST /admin/products/<id>/delete`
Archiva el producto (soft delete, no elimina físicamente).

---

### Importación / Exportación de Productos

#### `GET /admin/products/download-template`
Descarga un CSV vacío con las columnas esperadas para importación masiva.

**Respuesta:** archivo `plantilla_productos.csv`

#### `GET /admin/products/export-catalog`
Exporta el catálogo activo de productos en CSV (listo para reimportar).

**Respuesta:** archivo `catalogo_productos.csv`

#### `GET /admin/products/import`
Formulario de importación CSV.

#### `POST /admin/products/import`
Importa productos desde CSV. Usa lógica UPSERT: actualiza si el SKU existe, crea si no.

**Form params:** `file` (CSV)

**Respuesta:** renderiza resultado con conteo de `imported`, `updated`, `skipped`, `errors`.

---

### Mesas

#### `GET /admin/tables`
Lista todas las mesas.

#### `GET/POST /admin/tables/new`
Crea una mesa. **Form params:** `name`, `capacity`, `status`

#### `GET/POST /admin/tables/<id>/edit`
Edita una mesa existente.

#### `POST /admin/tables/<id>/delete`
Desactiva la mesa. Falla si tiene órdenes abiertas asociadas.

---

### Usuarios

#### `GET /admin/users`
Lista todos los usuarios.

#### `GET/POST /admin/users/new`
Crea un usuario. **Form params:** `username`, `full_name`, `password`, `role`

#### `GET/POST /admin/users/<id>/edit`
Edita un usuario. Permite cambiar contraseña opcionalmente.

#### `POST /admin/users/<id>/deactivate`
Desactiva un usuario. No permite auto-desactivación.

---

## Blueprint: `pos` — Punto de Venta

> Todas las rutas requieren `@cashier_required`.

### Dashboard

#### `GET /pos/dashboard`
Vista principal del POS. Muestra todas las mesas con estado de ocupación.

#### `GET /api/tables/status`
Estado en tiempo real de las mesas.

**Respuesta JSON:**
```json
[
  { "id": "uuid", "name": "Mesa 1", "status": "occupied" }
]
```

---

### Sesión de Caja

#### `GET /pos/register/open`
Formulario para abrir caja.

#### `POST /pos/register/open`
Abre una sesión de caja con el monto inicial.

**Form params:**
| Campo | Tipo | Descripción |
|---|---|---|
| opening_amount | decimal | efectivo inicial en caja |

#### `GET /pos/register/close`
Formulario para cerrar caja (muestra resumen de sesión).

#### `POST /pos/register/close`
Cierra la sesión activa. Calcula diferencia entre lo esperado y lo reportado.

**Form params:** `closing_amount` (decimal)

---

### Órdenes

#### `POST /pos/order/create`
Crea una nueva orden.

**Form params:** `table_id` (UUID o `"takeaway"`)

#### `GET /pos/order/table/<table_id>`
Vista de la orden activa en una mesa. Usar `takeaway` para para llevar.

#### `POST /pos/order/add-item`
Agrega un producto a la orden. Si ya existe, incrementa cantidad. Descuenta stock.

**Form params:**
| Campo | Descripción |
|---|---|
| order_id | UUID de la orden |
| product_id | UUID del producto |
| quantity | cantidad a agregar |

#### `POST /pos/order-item/<item_id>/remove`
Elimina un item de la orden. Restaura el stock.

#### `POST /pos/order-item/<item_id>/update-quantity`
Actualiza la cantidad de un item. Valida stock disponible.

**Form params:** `quantity` (integer)

#### `POST /pos/order/<order_id>/cancel`
Cancela la orden. Restaura todo el stock y libera la mesa.

---

### Pagos

#### `GET /pos/order/<order_id>/payment`
Formulario de cobro con el total de la orden.

#### `POST /pos/order/<order_id>/pay`
Procesa el pago. Si es efectivo, registra depósito en `CashMovement`.

**Form params:**
| Campo | Descripción |
|---|---|
| payment_method | `cash` / `card` / `transfer` |
| amount_received | monto entregado por el cliente |
| reference | número de transacción (card/transfer) |

#### `GET /pos/receipt/<order_id>`
Muestra el recibo del pago procesado.

---

### Menú

#### `GET /pos/menu`
Lista de productos activos disponibles para agregar a órdenes.

**Respuesta JSON:**
```json
[
  {
    "id": "uuid",
    "name": "Café Americano",
    "price": "5000.00",
    "stock": 50,
    "category": "Bebidas"
  }
]
```

---

## Blueprint: `cash` — Movimientos de Caja

> Requiere `@cashier_required`.

#### `POST /api/cash/movement`
Registra un retiro o depósito manual en la sesión activa.

**Request JSON:**
```json
{
  "session_id": "uuid",
  "amount": 50000,
  "type": "withdrawal",
  "description": "Pago de proveedor"
}
```

**Respuesta JSON exitosa:**
```json
{ "success": true, "balance": 150000 }
```

**Respuesta JSON error:**
```json
{ "success": false, "error": "Descripción del error" }
```
