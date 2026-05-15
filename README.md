# CoffeePOS - Documento de Alcance y Requisitos

**Versión:** 1.0  
**Fecha:** 13 de febrero de 2025  
**Autor:** [@Crespitosoff](https://github.com/Crespitosoff)  

**Proyecto:** Sistema de Punto de Venta para Cafetería

---

## 1. ALCANCE DEL PROYECTO

### 1.1 Descripción General
Sistema web de punto de venta (POS) para cafeterías que permite gestionar órdenes, productos, inventario, usuarios y control de caja. Desarrollado con Python/Flask y PostgreSQL.

### 1.2 Objetivo
Crear un POS funcional y profesional que sirva como proyecto académico de último semestre y como pieza de portafolio, demostrando competencias en desarrollo backend con Python, arquitectura MVC, gestión de bases de datos relacionales y desarrollo full-stack.

### 1.3 QUÉ INCLUYE EL PROYECTO

**Gestión de Productos:**
- CRUD completo de productos
- Categorización de productos
- Control de stock
- Indicadores de stock bajo
- Importación masiva vía CSV/Excel

**Punto de Venta (POS):**
- Visualización de mesas disponibles/ocupadas
- Creación y gestión de órdenes
- Selección de productos por categoría
- Carrito de compra en tiempo real
- Proceso de pago con múltiples métodos
- Cálculo automático de cambio
- Generación de recibos imprimibles

**Gestión de Usuarios:**
- CRUD de usuarios (admin/cashier)
- Sistema de autenticación
- Control de acceso basado en roles (RBAC)

**Control de Caja:**
- Apertura de caja con monto inicial
- Registro de transacciones
- Cierre de caja con cálculo de diferencias
- Resumen de ventas por turno

**Reportes Básicos:**
- Ventas por turno
- Desglose por método de pago
- Diferencias de caja

**Configuración y Auditoría:**
- Parámetros globales del negocio (Store Settings) incluyendo prefijos de facturación (ej. FAC-) y datos de contacto.
- Trazabilidad y auditoría en base de datos con columnas `created_at`, `updated_at` y `closed_at`.
- Registro persistente del cálculo de cambio (`change`) en los pagos.
- Manejo estandarizado de zonas horarias (America/Bogota) en transacciones.

### 1.4 QUÉ NO INCLUYE EL PROYECTO

**Funcionalidades Excluidas:**
- ❌ Modificadores de productos (extra shot, leche alternativa, etc.)
- ❌ Propinas (tips)
- ❌ Sistema de descuentos y cupones
- ❌ Reportes avanzados con gráficas
- ❌ Dashboard analítico con KPIs
- ❌ Exportación a Excel/PDF de reportes
- ❌ Gestión de proveedores
- ❌ Órdenes de compra
- ❌ Sistema de reservas
- ❌ Integración con sistemas de pago externos (Stripe, PayPal)
- ❌ Programa de lealtad/puntos
- ❌ Sistema de delivery/domicilios
- ❌ App móvil nativa
- ❌ Notificaciones push
- ❌ Facturación electrónica
- ❌ Multi-sucursal
- ❌ Multi-idioma
- ❌ Modo offline

**Límites Técnicos:**
- Máximo 2 roles de usuario (admin, cashier)
- Una sesión de caja por usuario
- Sin soporte para múltiples monedas
- Sin sistema de auditoría detallado (accounting_ledger)

---

## 2. REQUISITOS FUNCIONALES

### RF-001: Autenticación de Usuarios
**Descripción:** El sistema debe permitir login con username y password.  
**Prioridad:** Alta  
**Criterios:**
- Validación de credenciales contra BD
- Passwords hasheados (Werkzeug)
- Sesión persistente (Flask-Login)
- Logout funcional

### RF-002: Control de Acceso por Roles
**Descripción:** El sistema debe restringir funcionalidades según rol.  
**Prioridad:** Alta  
**Criterios:**
- Rol admin: acceso total
- Rol cashier: solo POS y caja
- Decoradores @admin_required, @cashier_required
- Página de error 403 para accesos no autorizados

### RF-003: CRUD de Productos
**Descripción:** Admin puede crear, leer, actualizar y eliminar productos.  
**Prioridad:** Alta  
**Criterios:**
- Campos: nombre, categoría, precio, stock
- Soft delete (is_active = False)
- Validación: precio > 0, stock >= 0

### RF-004: CRUD de Categorías
**Descripción:** Admin puede gestionar categorías de productos.  
**Prioridad:** Media  
**Criterios:**
- Campos: nombre, descripción
- Al menos 5 categorías predefinidas en seed

### RF-005: Importación Masiva de Productos
**Descripción:** Admin puede cargar productos desde archivo CSV.  
**Prioridad:** Media  
**Criterios:**
- Template CSV descargable
- Exportación del catálogo activo completo
- Validación de formato y datos al vuelo (Upsert)
- Reporte de errores por fila
- Uso del módulo nativo `csv` de Python (sin dependencias externas)

### RF-006: CRUD de Usuarios
**Descripción:** Admin puede gestionar usuarios del sistema.  
**Prioridad:** Alta  
**Criterios:**
- Campos: username (único), password, nombre completo, rol
- Solo puede crear admin o cashier
- No puede desactivarse a sí mismo

### RF-007: Visualización de Mesas
**Descripción:** Cajero y Admin ven estado de todas las mesas en dashboard.  
**Prioridad:** Alta  
**Criterios:**
- Estados: disponible (verde), ocupada (rojo)
- Visión global independiente de la sesión de caja (todas las órdenes OPEN)
- Click en mesa abre orden
- Actualización en tiempo real vía short-polling (fetch/AJAX) sin recargar la página

### RF-008: Creación de Orden
**Descripción:** Cajero puede crear orden para una mesa.  
**Prioridad:** Alta  
**Criterios:**
- Asociada a mesa y usuario (cajero)
- Estado inicial: pending
- Mesa pasa a ocupada automáticamente

### RF-009: Agregar Productos a Orden
**Descripción:** Cajero puede agregar productos a una orden con cantidad.  
**Prioridad:** Alta  
**Criterios:**
- Selección por categoría
- Input de cantidad
- Actualización de carrito sin reload (AJAX)
- Validación de stock disponible
- Decremento automático de stock

### RF-010: Modificar Cantidad de Items
**Descripción:** Cajero puede cambiar cantidad de items en carrito.  
**Prioridad:** Media  
**Criterios:**
- Botones +/- para ajustar
- Recálculo de subtotal en tiempo real
- Ajuste de stock del producto

### RF-011: Eliminar Items de Orden
**Descripción:** Cajero puede quitar productos del carrito.  
**Prioridad:** Media  
**Criterios:**
- Botón X por item
- Devolución de stock al producto
- Recálculo de total

### RF-012: Proceso de Pago
**Descripción:** Cajero puede procesar pago de una orden.  
**Prioridad:** Alta  
**Criterios:**
- Métodos: efectivo, tarjeta, transferencia
- Si efectivo: input de monto recibido, cálculo de cambio
- Si tarjeta/transferencia: monto = total automático
- Validación: monto recibido >= total

### RF-013: Generación de Recibo
**Descripción:** Sistema genera recibo imprimible después del pago.  
**Prioridad:** Alta  
**Criterios:**
- Formato ticket 80mm
- Incluye: items, total, método de pago, cambio, cajero, fecha/hora
- Botón imprimir (window.print())
- CSS específico para impresión

### RF-014: Liberación de Mesa
**Descripción:** Mesa vuelve a disponible al completar pago.  
**Prioridad:** Alta  
**Criterios:**
- Cambio automático al pagar
- current_order_id = NULL
- status = 'available'

### RF-015: Apertura de Caja
**Descripción:** Cajero abre su caja al inicio del turno.  
**Prioridad:** Alta  
**Criterios:**
- Input: monto inicial en efectivo
- Validación: un cajero solo puede tener una sesión abierta
- Registro: RegisterSession con status='open'

### RF-016: Cierre de Caja
**Descripción:** Cajero cierra caja al final del turno.  
**Prioridad:** Alta  
**Criterios:**
- Resumen: órdenes procesadas, total vendido, desglose por método
- Cálculo: efectivo esperado = inicial + ventas en efectivo
- Input: efectivo contado
- Mostrar diferencia (positiva/negativa)
- No permitir cierre si hay órdenes pending

### RF-017: Indicador de Stock Bajo
**Descripción:** Sistema alerta cuando stock < 10 unidades.  
**Prioridad:** Baja  
**Criterios:**
- Badge visual en lista de productos
- Color de alerta (rojo o amarillo)

### RF-018: Búsqueda de Productos
**Descripción:** Admin puede buscar productos por nombre.  
**Prioridad:** Baja  
**Criterios:**
- Input de búsqueda en panel admin
- Filtrado en tiempo real (JavaScript)

### RF-019: Filtro por Categoría
**Descripción:** Admin puede filtrar productos por categoría.  
**Prioridad:** Baja  
**Criterios:**
- Select de categorías
- Actualiza tabla sin reload

### RF-020: Cancelación de Orden
**Descripción:** Cajero puede cancelar una orden antes de pagar.  
**Prioridad:** Media  
**Criterios:**
- Confirmación requerida
- Devolución de stock de todos los items
- Orden status = 'cancelled'
- Mesa queda disponible

---

## 3. REQUISITOS NO FUNCIONALES

### RNF-001: Rendimiento
- Tiempo de respuesta < 2 segundos para operaciones CRUD
- Carga de dashboard POS < 1 segundo
- Soporte para 50 órdenes concurrentes sin degradación

### RNF-002: Seguridad
- Passwords hasheados con Werkzeug (PBKDF2)
- Protección CSRF en formularios
- Sesiones con SECRET_KEY fuerte
- Control de acceso en todas las rutas sensibles
- Validación de inputs (backend y frontend)
- SQL injection prevenido (SQLAlchemy ORM)

### RNF-003: Usabilidad
- Interfaz responsive (desktop, tablet, mobile)
- Diseño mobile-first
- Mensajes de error claros y descriptivos
- Confirmaciones antes de acciones destructivas
- Loading indicators para operaciones asíncronas
- Navegación intuitiva (máximo 3 clicks para cualquier función)

### RNF-004: Mantenibilidad
- Código modular con Blueprints
- Separación de lógica en capa de servicios
- Nomenclatura consistente (PEP 8 para Python)
- Comentarios en lógica compleja
- Documentación técnica completa

### RNF-005: Escalabilidad
- Arquitectura preparada para agregar nuevas funcionalidades
- Schema de BD normalizado
- Índices en columnas de búsqueda frecuente

### RNF-006: Compatibilidad
- Navegadores: Chrome 90+, Firefox 88+, Safari 14+
- SQLite (Desarrollo local) / PostgreSQL 15+ (Producción)
- Python 3.10+
- Funciona en desarrollo local sin dependencias restrictivas (Windows/Linux/Mac)

### RNF-007: Disponibilidad
- Sistema funcional 24/7 en producción (si se despliega)
- Backup automático de BD (opcional en producción)

### RNF-008: Integridad de Datos
- Transacciones ACID en operaciones críticas
- Constraints de BD (FK, UNIQUE, NOT NULL)
- Validaciones de negocio en capa de servicios

---

## 4. ROLES DE USUARIO

### 4.1 ROL: Administrador (admin)

**Permisos:**
- ✅ Acceso completo al sistema
- ✅ CRUD de productos
- ✅ CRUD de usuarios
- ✅ Importación masiva de productos
- ✅ Acceso a todas las funciones del cajero
- ✅ Configuración del sistema

**Restricciones:**
- ❌ No puede desactivarse a sí mismo

**Usuario por defecto:**
- Username: `admin`
- Password: `admin123`

---

### 4.2 ROL: Cajero (cashier)

**Permisos:**
- ✅ Acceso al módulo POS
- ✅ Crear y gestionar órdenes
- ✅ Procesar pagos
- ✅ Apertura y cierre de su propia caja
- ✅ Ver productos (solo lectura)

**Restricciones:**
- ❌ No puede acceder al panel admin
- ❌ No puede crear/editar/eliminar productos
- ❌ No puede crear/editar/eliminar usuarios
- ❌ No puede ver sesiones de caja de otros cajeros

**Usuario por defecto:**
- Username: `cashier`
- Password: `cashier123`

---

## 5. STACK TECNOLÓGICO

### 5.1 Backend
| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Python** | 3.10+ | Lenguaje de programación principal |
| **Flask** | 3.0 | Framework web minimalista |
| **SQLAlchemy** | 2.0 | ORM para interacción con BD |
| **Flask-Login** | 0.6+ | Gestión de sesiones de usuario |
| **Flask-Migrate** | 4.0+ | Migraciones de BD (Alembic) |
| **Werkzeug** | 3.0+ | Utilidades (hashing passwords) |
| **python-dotenv** | 1.0+ | Gestión de variables de entorno |
| **csv (nativo)** | - | Procesamiento de archivos CSV (Upsert y Exportación) |

### 5.2 Base de Datos
| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **SQLite / PostgreSQL** | 3+ / 15+ | Base de datos relacional (Dev / Prod) |
| **psycopg2-binary** | 2.9+ | Driver PostgreSQL para Python (Solo producción) |

### 5.3 Frontend
| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Jinja2** | 3.1+ | Motor de templates (viene con Flask) |
| **Tailwind CSS** | 3.4+ (CDN) | Framework CSS utility-first |
| **Vanilla JavaScript** | ES6+ | Interactividad (AJAX, validaciones) |

### 5.4 Herramientas de Desarrollo
| Herramienta | Propósito |
|-------------|-----------|
| **Git** | Control de versiones |
| **GitHub** | Repositorio remoto |
| **Jira** | Gestión de proyecto (Scrum/Kanban) |
| **pytest** | Testing unitario |
| **VSCode** | IDE principal |
| **DBeaver** | Cliente PostgreSQL (opcional) |

### 5.5 Despliegue (Opcional)
| Plataforma | Propósito |
|------------|-----------|
| **Render** | Hosting de aplicación y BD |
| **Railway** | Alternativa de hosting |
| **Gunicorn** | WSGI server para producción |

---

## 6. ESTRUCTURA DEL PROYECTO
```
├── .github
│   └── CODEOWNERS
├── app
│   ├── models
│   │   ├── __init__.py
│   │   └── domain.py
│   ├── routes
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── auth.py
│   │   ├── cash.py
│   │   └── pos.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── cash_movement_service.py
│   │   ├── import_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   ├── product_service.py
│   │   ├── register_service.py
│   │   ├── report_service.py
│   │   └── user_service.py
│   ├── templates
│   │   ├── admin
│   │   │   ├── dashboard.html
│   │   │   ├── product_form.html
│   │   │   ├── products.html
│   │   │   ├── user_form.html
│   │   │   └── users.html
│   │   ├── auth
│   │   │   └── login.html
│   │   ├── errors
│   │   │   └── 403.html
│   │   ├── layout
│   │   │   └── base.html
│   │   └── pos
│   │       ├── dashboard.html
│   │       ├── order.html
│   │       ├── payment.html
│   │       ├── receipt.html
│   │       ├── register_close.html
│   │       └── register_open.html
│   ├── utils
│   │   └── decorators.py
│   ├── __init__.py
│   └── extensions.py
├── docs
│   ├── stitch_coffeepos_login_interface
│   │   ├── the_elevated_harvest_design_system
│   │   │   └── DESIGN.md
│   │   └── design.md
│   ├── CoffeePOS.sql
│   ├── diagram.png
│   └── seed_flask_shell.py
├── migrations
│   ├── versions
│   │   └── 64d1cfeb4f4b_initial_migration_with_refactored_models.py
│   ├── README
│   ├── alembic.ini
│   ├── env.py
│   └── script.py.mako
├── .gitignore
├── JiraTodasLasActividades.csv
├── README.md
├── config.py
├── run.py
└── seed.py
```

---


## APROBACIONES

**Desarrolladores:** 
- Backend: [@Crespitosoff](https://github.com/Crespitosoff)
- Frontend: [@cortesperdomojulian6-max](https://github.com/cortesperdomojulian6-max)
- Integrador: [@Tomas-Hack1](https://github.com/Tomas-Hack1)  

**Fecha de aprobación:** 13 de febrero de 2025  

**Revisiones:**
- v1.0 (13/02/2025): Documento inicial
- v1.1 (14/05/2026): Actualización de requerimientos, eliminación de Pandas, soporte para SQLite, mejoras en UI, exportación CSV y UI responsiva.
