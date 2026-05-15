# CoffeePOS — Sistema de Punto de Venta para Cafetería

Sistema web para gestión de órdenes, productos, inventario, usuarios y control de caja en cafeterías. Desarrollado con Python/Flask y PostgreSQL.

**Equipo:**
- Backend: [@Crespitosoff](https://github.com/Crespitosoff)
- Frontend: [@cortesperdomojulian6-max](https://github.com/cortesperdomojulian6-max)
- Integrador: [@Tomas-Hack1](https://github.com/Tomas-Hack1)

---

## Requisitos Previos

Antes de instalar, asegúrate de tener:

| Herramienta | Versión mínima | Verificar con |
|---|---|---|
| Python | 3.10+ | `python --version` |
| PostgreSQL | 15+ | `psql --version` |
| Git | cualquier versión | `git --version` |

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Tomas-Hack1/CoffeePOS.git
cd CoffeePOS
```

### 2. Crear y activar el entorno virtual

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Esto instala automáticamente los paquetes principales:

| Paquete | Descripción |
|---|---|
| `Flask` | Framework web |
| `Flask-SQLAlchemy` | ORM para la base de datos |
| `Flask-Migrate` | Migraciones con Alembic |
| `Flask-Login` | Gestión de sesiones de usuario |
| `psycopg2-binary` | Driver de conexión a PostgreSQL |
| `python-dotenv` | Lectura del archivo `.env` |
| `Werkzeug` | Hashing de contraseñas |
| `gunicorn` | Servidor WSGI para producción |

> La lista completa está en [`requirements.txt`](requirements.txt).

### 4. Crear la base de datos en PostgreSQL

Abre **pgAdmin** o **psql** y ejecuta:

```sql
CREATE DATABASE coffeepos_db;
```

### 5. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto con este contenido:

```env
DATABASE_URL=postgresql://postgres:TU_PASSWORD@localhost:5432/coffeepos_db

SECRET_KEY=cambia-esto-por-una-clave-larga-y-aleatoria
JWT_SECRET_KEY=cambia-esto-por-otra-clave-larga-y-aleatoria
```

Reemplaza `postgres` y `TU_PASSWORD` con tu usuario y contraseña de PostgreSQL.

> Para generar claves seguras: `python -c "import secrets; print(secrets.token_hex(32))"`

### 6. Aplicar las migraciones

```bash
flask db upgrade
```

### 7. Cargar los datos iniciales (seed)

```bash
python seed.py
```

Esto crea:
- Usuarios de prueba (ver [Credenciales por defecto](#credenciales-por-defecto))
- 5 categorías y 15 productos de ejemplo
- 8 mesas
- Configuración de la tienda

### 8. Ejecutar la aplicación

```bash
python run.py
```

Abre tu navegador en: **http://localhost:5000**

---

## Credenciales por defecto

| Rol | Usuario | Contraseña | Acceso |
|---|---|---|---|
| Administrador | `admin` | `admin123` | Panel admin + POS |
| Administrador suplente | `adminsuple` | `adminsuple123` | Panel admin + POS |
| Cajero | `cajero1` | `cajero1123` | Solo POS |
| Cajero | `cajero2` | `cajero2123` | Solo POS |

> **Importante:** Cambia estas contraseñas antes de desplegar en producción.

---

## Flujo de uso básico

1. Inicia sesión como **cajero**
2. Abre la caja ingresando el monto inicial de efectivo
3. Selecciona una mesa desde el dashboard
4. Agrega productos a la orden
5. Procesa el pago (efectivo, tarjeta o transferencia)
6. Al finalizar el turno, cierra la caja

Como **admin** puedes además gestionar productos, usuarios, mesas y ver los reportes de auditoría.

---

## Estructura del Proyecto

```
CoffeePOS/
├── app/
│   ├── __init__.py          # App factory
│   ├── extensions.py        # SQLAlchemy y Migrate
│   ├── models/domain.py     # Modelos y enums
│   ├── routes/              # Blueprints HTTP
│   │   ├── auth.py          # Login / logout
│   │   ├── admin.py         # Panel administración
│   │   ├── pos.py           # Punto de venta
│   │   └── cash.py          # API movimientos de caja
│   ├── services/            # Lógica de negocio
│   └── utils/decorators.py  # Control de acceso por rol
├── docs/                    # Documentación técnica
│   ├── ARCHITECTURE.md      # Arquitectura y decisiones de diseño
│   ├── DATABASE.md          # Modelos y esquema de BD
│   ├── API.md               # Rutas y endpoints
│   ├── SERVICES.md          # Descripción de servicios
│   ├── seed_flask_shell.py  # Flujo de demostración desde Flask shell
│   └── CoffeePOS.sql        # Script SQL del esquema de la BD
├── migrations/              # Migraciones Alembic
├── config.py                # Configuración desde .env
├── run.py                   # Punto de entrada
└── seed.py                  # Datos iniciales
```

Para documentación técnica detallada ver la carpeta [`docs/`](docs/).

---

## Comandos útiles

```bash
# Crear nueva migración tras modificar modelos
flask db migrate -m "descripcion del cambio"

# Aplicar migraciones pendientes
flask db upgrade

# Revertir última migración
flask db downgrade

# Reinstalar dependencias
pip install -r requirements.txt
```

---

## Stack Tecnológico

### Backend
| Tecnología | Versión | Propósito |
|---|---|---|
| **Python** | 3.10+ | Lenguaje principal |
| **Flask** | 3.0 | Framework web |
| **SQLAlchemy** | 2.0 | ORM para la BD |
| **Flask-Login** | 0.6+ | Gestión de sesiones |
| **Flask-Migrate** | 4.0+ | Migraciones (Alembic) |
| **Werkzeug** | 3.0+ | Hashing de contraseñas |
| **python-dotenv** | 1.0+ | Variables de entorno |
| **csv (nativo)** | — | Importación/exportación CSV |

### Base de Datos
| Tecnología | Versión | Propósito |
|---|---|---|
| **PostgreSQL** | 15+ | BD relacional (producción) |
| **psycopg2-binary** | 2.9+ | Driver PostgreSQL para Python |

### Frontend
| Tecnología | Propósito |
|---|---|
| **Jinja2** | Motor de templates |
| **Tailwind CSS** | Framework CSS (CDN) |
| **JavaScript ES6+** | Interactividad y AJAX |

---

## Funcionalidades

**Punto de Venta (POS):**
- Dashboard de mesas con estado en tiempo real (short-polling)
- Creación y gestión de órdenes por mesa o para llevar
- Pago en efectivo, tarjeta o transferencia
- Cálculo automático de cambio y generación de recibo imprimible

**Gestión de Caja:**
- Apertura con monto inicial
- Registro de retiros y depósitos manuales
- Cierre con cálculo de diferencia (real vs esperado)
- Auditoría y detección de movimientos sospechosos

**Panel de Administración:**
- CRUD completo de productos, usuarios y mesas
- Importación y exportación masiva de productos vía CSV (con lógica UPSERT)
- Reportes de ventas y auditoría de caja por rango de fechas

---

## Alcance del Proyecto

### Incluye
- CRUD de productos con control de stock e indicadores de stock bajo
- Categorización de productos
- Importación masiva vía CSV con validación por fila
- Sistema de autenticación con roles (admin / cashier)
- Órdenes por mesa y para llevar
- Múltiples métodos de pago
- Control de caja por turno con trazabilidad de efectivo
- Reportes de ventas y auditoría

### No incluye
- Modificadores de productos (extra shot, leche alternativa, etc.)
- Sistema de descuentos y cupones
- Reportes con gráficas
- Integración con pasarelas de pago externas
- Facturación electrónica
- Multi-sucursal / multi-idioma
- App móvil nativa / modo offline

---

## Requisitos Funcionales Destacados

| ID | Descripción | Prioridad |
|---|---|---|
| RF-001 | Autenticación con username y password | Alta |
| RF-002 | Control de acceso por roles (admin / cashier) | Alta |
| RF-003 | CRUD de productos con soft delete | Alta |
| RF-005 | Importación CSV con UPSERT por SKU y exportación del catálogo | Media |
| RF-007 | Dashboard de mesas con estado global en tiempo real | Alta |
| RF-012 | Proceso de pago con múltiples métodos | Alta |
| RF-013 | Generación de recibo imprimible (formato 80mm) | Alta |
| RF-015 | Apertura de caja con monto inicial | Alta |
| RF-016 | Cierre de caja con cálculo de diferencia | Alta |
| RF-020 | Cancelación de orden con devolución de stock | Media |

## Requisitos No Funcionales Destacados

| ID | Descripción |
|---|---|
| RNF-002 | Passwords hasheados (Werkzeug PBKDF2), SQL injection prevenido por ORM |
| RNF-003 | Interfaz responsive (desktop, tablet, mobile) |
| RNF-004 | Código modular con Blueprints y capa de servicios (PEP 8) |
| RNF-006 | Compatible con Chrome 90+, Firefox 88+, Safari 14+ / Python 3.10+ |
| RNF-008 | Transacciones ACID, constraints de BD, validaciones en servicios |

---

## Aprobaciones

**Desarrolladores:**
- Backend: [@Crespitosoff](https://github.com/Crespitosoff)
- Frontend: [@cortesperdomojulian6-max](https://github.com/cortesperdomojulian6-max)
- Integrador: [@Tomas-Hack1](https://github.com/Tomas-Hack1)

**Revisiones:**
- v1.0 (13/02/2025): Documento inicial
- v1.1 (14/05/2026): Actualización de requerimientos, soporte PostgreSQL, importación CSV con UPSERT, instrucciones de instalación y documentación técnica.
