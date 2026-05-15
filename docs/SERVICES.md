# Servicios — CoffeePOS

La capa de servicios contiene **toda la lógica de negocio**. Las rutas solo validan la entrada HTTP y delegan a estos servicios. Ningún servicio accede directamente a variables de Flask (request, session); reciben todo como parámetros.

---

## `product_service.py`

Gestión del catálogo de productos e inventario.

| Función | Descripción |
|---|---|
| `get_all_products(category_id, active_only)` | Lista productos con filtros opcionales |
| `get_product_by_id(product_id)` | Obtiene un producto por UUID |
| `create_product(**kwargs)` | Crea producto nuevo |
| `update_product(product_id, **kwargs)` | Actualiza campos del producto |
| `delete_product(product_id)` | Soft delete — marca como `ARCHIVED` |
| `update_stock(product_id, quantity)` | Ajusta el stock (positivo o negativo) |

---

## `user_service.py`

Gestión de usuarios del sistema.

| Función | Descripción |
|---|---|
| `get_all_users(active_only)` | Lista usuarios, opcionalmente solo activos |
| `get_user_by_id(user_id)` | Busca por UUID |
| `get_user_by_username(username)` | Busca por nombre de usuario |
| `create_user(username, full_name, password, role)` | Crea usuario con contraseña hasheada |
| `update_user(user_id, **kwargs)` | Actualiza campos, permite cambio de contraseña |
| `delete_user(user_id)` | Soft delete — marca como `INACTIVE` |
| `change_password(user_id, new_password)` | Actualiza solo la contraseña |

---

## `order_service.py`

Ciclo de vida completo de las órdenes.

| Función | Descripción |
|---|---|
| `create_order(session_id, user_id, table_id)` | Crea orden en estado `OPEN` |
| `add_item_to_order(order_id, product_id, quantity)` | Agrega producto; fusiona duplicados; descuenta stock; recalcula totales |
| `remove_item_from_order(item_id)` | Elimina item; restaura stock; recalcula totales |
| `update_item_quantity(item_id, quantity)` | Ajusta cantidad validando stock disponible |
| `cancel_order(order_id)` | Cancela orden; restaura todo el stock; libera la mesa |
| `calculate_order_total(order_id)` | Persiste subtotal, impuesto y total calculados |

**Notas:**
- Los totales usan `decimal.Decimal` en todo momento.
- La tasa de IVA se lee desde `StoreSetting` (por defecto 19%).
- El `base_price` y `historical_cost` se copian del producto al momento de agregar el item — los precios futuros no afectan órdenes pasadas.

---

## `payment_service.py`

Procesamiento de pagos y generación de recibos.

| Función | Descripción |
|---|---|
| `get_payment_methods()` | Retorna lista de métodos disponibles |
| `process_payment(order_id, method, amount_received, reference)` | Valida y procesa el pago; marca orden como `PAID`; registra depósito si es efectivo |
| `generate_receipt(order_id)` | Construye dict con todos los datos del recibo |

**Flujo de `process_payment`:**
1. Verifica que la orden esté en estado `OPEN` y tenga items.
2. Verifica que `amount_received >= total`.
3. Crea registro en `Payment`.
4. Marca orden como `PAID`.
5. Si el método es `CASH` → llama a `cash_movement_service.record_deposit()`.
6. Retorna el monto de cambio.

---

## `register_service.py`

Gestión del turno de caja (apertura y cierre).

| Función | Descripción |
|---|---|
| `get_active_session(user_id)` | Retorna la sesión `OPEN` del cajero, o `None` |
| `get_session_by_id(session_id)` | Busca sesión por UUID |
| `get_session_summary(session_id)` | Resumen completo: ventas por método, retiros/depósitos manuales, efectivo esperado, diferencia |
| `open_register(user_id, opening_amount)` | Crea nueva sesión y registra movimiento de apertura |
| `close_register(session_id, user_id, closing_amount)` | Cierra sesión; verifica que no haya órdenes abiertas; calcula y persiste diferencia |

**Restricción de cierre:** no se puede cerrar la caja si existen órdenes con estado `OPEN` o `PREPARING` en la sesión.

---

## `cash_movement_service.py`

Trazabilidad de cada movimiento de efectivo. Es el único lugar donde se escriben registros en `CashMovement`.

| Función | Descripción |
|---|---|
| `record_opening(session_id, user_id, amount)` | Registra apertura de caja |
| `record_closing(session_id, user_id, amount, expected, difference)` | Registra cierre con diferencia calculada |
| `record_withdrawal(session_id, user_id, amount, description)` | Retiro manual (resta del saldo) |
| `record_deposit(session_id, user_id, amount, description)` | Depósito manual o venta en efectivo (suma al saldo) |
| `record_adjustment(session_id, user_id, amount, description)` | Ajuste por discrepancia |
| `get_session_movements(session_id)` | Todos los movimientos de una sesión |
| `get_cashier_movements(user_id, start_date, end_date)` | Movimientos filtrados por cajero y fecha |
| `get_all_movements(start_date, end_date)` | Vista global para auditoría |

**Cómo funciona `_execute_movement`:**
1. Obtiene `balance_after` del último movimiento (o 0 si es el primero).
2. Calcula nuevo `balance_after = balance_before + amount`.
3. Persiste el registro. Todo en una sola transacción.

---

## `report_service.py`

Reportes de auditoría y detección de irregularidades para el admin.

| Función | Descripción |
|---|---|
| `get_register_audit_trail(start_date, end_date)` | Lista de sesiones con duración, ventas por método, estado de discrepancia y alertas de retiros sospechosos |
| `get_session_detail(session_id)` | Detalle completo de una sesión: órdenes y movimientos |
| `get_daily_sales_summary(date)` | Totales del día por método de pago, lista de cajeros, alerta si hay caja abierta |
| `get_suspicious_movements(threshold, start_date, end_date)` | Retiros por encima del umbral o sin justificación |
| `count_open_sessions()` | Cantidad de cajas abiertas en este momento |

**Criterio de movimiento sospechoso (`_is_suspicious_movement`):**
- Tipo `WITHDRAWAL` **y** (`amount > threshold` **o** `description` está vacía).

---

## `import_service.py`

Importación y exportación masiva de productos vía CSV.

| Función | Descripción |
|---|---|
| `process_csv(file)` | Importa productos: UPSERT por SKU, crea categorías faltantes, retorna estadísticas |
| `export_catalog_csv()` | Exporta catálogo activo con BOM UTF-8 (compatible con Excel) |

**Columnas esperadas en CSV:**
`sku`, `name`, `price`, `cost`, `stock`, `min_stock`, `category`, `description`, `status`

El servicio acepta alias en inglés y español para los encabezados. Si un SKU ya existe, actualiza el producto; si no, lo crea. Las categorías inexistentes se crean automáticamente con un slug generado.

**Retorno de `process_csv`:**
```python
{
    "imported": 10,   # productos nuevos creados
    "updated": 3,     # productos existentes actualizados
    "skipped": 1,     # filas inválidas ignoradas
    "errors": [...]   # lista de mensajes de error por fila
}
```
