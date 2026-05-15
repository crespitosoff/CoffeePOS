# Arquitectura del Sistema — CoffeePOS

## Visión General

Es una aplicación web construida con **Flask** y **PostgreSQL**, orientada a puntos de venta (POS) para cafeterías. Sigue el patrón **MVC con capa de servicios** para separar la lógica de negocio de las rutas HTTP.

---

## Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Web framework | Flask 3.1 |
| ORM | SQLAlchemy 2.0 |
| Migraciones | Flask-Migrate|
| Autenticación | Flask-Login |
| Base de datos | PostgreSQL |
| Templates | Jinja2 |
| Servidor producción | Gunicorn |

---

## Estructura de Carpetas

```
CoffeePOS/
├── app/
│   ├── __init__.py          # App factory (create_app)
│   ├── extensions.py        # Instancias db y migrate
│   ├── models/
│   │   └── domain.py        # Todos los modelos y enums
│   ├── routes/              # Blueprints HTTP (controladores)
│   │   ├── auth.py          # Login / logout
│   │   ├── admin.py         # Panel de administración
│   │   ├── pos.py           # Operaciones de caja
│   │   └── cash.py          # API de movimientos de efectivo
│   ├── services/            # Lógica de negocio
│   │   ├── product_service.py
│   │   ├── user_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   ├── register_service.py
│   │   ├── cash_movement_service.py
│   │   ├── report_service.py
│   │   └── import_service.py
│   ├── utils/
│   │   └── decorators.py    # Control de acceso por rol
│   └── templates/           # Plantillas Jinja2
├── config.py                # Configuración desde .env
├── run.py                   # Punto de entrada
├── migrations/              # Migraciones Alembic
└── docs/                    # Documentación técnica
```

---

## Patrón de Capas

```
Request HTTP
    │
    ▼
[ Routes / Blueprints ]   ← Valida entrada, llama servicios, renderiza respuesta
    │
    ▼
[ Services ]              ← Toda la lógica de negocio vive aquí
    │
    ▼
[ Models / SQLAlchemy ]   ← Mapeo objeto-relacional, constraints e índices
    │
    ▼
[ PostgreSQL ]
```

**Regla clave:** Las rutas nunca tocan la base de datos directamente — siempre delegan a un servicio.

---

## Autenticación y Autorización

- **Flask-Login** gestiona sesiones de usuario con cookies.
- El `user_loader` reconstruye el usuario desde UUID guardado en la sesión.
- Dos decoradores en `utils/decorators.py` protegen las rutas:
  - `@admin_required` — solo rol `admin`
  - `@cashier_required` — roles `cashier` y `admin`

---

## Decisiones de Diseño Importantes

### Claves primarias UUID
Todos los modelos usan `gen_random_uuid()` de PostgreSQL. Evita colisiones en entornos distribuidos y no expone secuencias predecibles.

### `Decimal` para valores monetarios
Todo cálculo financiero usa `decimal.Decimal` en lugar de `float` para evitar errores de punto flotante en sumas de dinero.

### Borrado lógico (soft delete)
Los productos, usuarios y tablas nunca se eliminan físicamente. Se marcan con estado `archived` / `inactive`, preservando el historial de órdenes.

### Una sola caja abierta por usuario
Un índice único parcial en `RegisterSession` impide que el mismo cajero abra dos cajas simultáneamente.

### Trazabilidad de efectivo
Todo movimiento de caja (apertura, cierre, retiro, depósito, pago en efectivo) pasa por `CashMovementService`, que mantiene un saldo corrido para auditoría y detección de irregularidades.

---

## Flujo Principal de Operación

```
1. Cajero abre sesión de caja  →  register_service.open_register()
2. Cliente pide en mesa o para llevar
3. Cajero crea orden             →  order_service.create_order()
4. Cajero agrega productos       →  order_service.add_item_to_order()
   (el stock se descuenta aquí)
5. Cajero procesa el pago        →  payment_service.process_payment()
   (si es efectivo → cash_movement_service.record_deposit())
6. Cajero cierra caja            →  register_service.close_register()
   (se calcula diferencia esperado vs real)
7. Admin revisa reportes         →  report_service.*
```
