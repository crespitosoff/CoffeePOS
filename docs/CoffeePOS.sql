-- =====================================================
-- COFFEEPOS DB
-- =====================================================

-- EXTENSIÓN NECESARIA PARA UUID
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =====================================================
-- ENUMS
-- =====================================================

-- Roles de usuario
CREATE TYPE user_role AS ENUM (
  'admin',
  'cashier'
);

-- Estado de usuario
CREATE TYPE user_status AS ENUM (
  'active',
  'inactive',
  'suspended',
  'terminated'
);

-- Estado genérico (productos, categorías, mesas)
CREATE TYPE generic_status AS ENUM (
  'active',
  'inactive',
  'archived'
);

-- Estado de órdenes
CREATE TYPE order_status AS ENUM (
  'open',
  'preparing',
  'ready',
  'paid',
  'cancelled'
);

-- Métodos de pago
CREATE TYPE payment_method AS ENUM (
  'cash',
  'card',
  'transfer'
);

-- Estado de caja
CREATE TYPE register_status AS ENUM (
  'open',
  'closed'
);

-- =====================================================
-- CONFIGURACIÓN DEL NEGOCIO
-- =====================================================

CREATE TABLE store_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  business_name VARCHAR(150) NOT NULL,
  commercial_name VARCHAR(150),
  tax_id VARCHAR(50),

  address TEXT,
  phone VARCHAR(30),
  email VARCHAR(120),
  website VARCHAR(150),

  -- Configuración regional
  currency VARCHAR(10) DEFAULT 'COP',
  language VARCHAR(10) DEFAULT 'es-CO',
  timezone VARCHAR(60) DEFAULT 'America/Bogota',
  country_code VARCHAR(5) DEFAULT 'CO',

  -- Impuestos
  tax_percentage NUMERIC(5,2) DEFAULT 19 CHECK (tax_percentage >= 0),

  -- Facturación
  invoice_prefix VARCHAR(20) DEFAULT 'FAC',
  next_invoice_number INT DEFAULT 1,

  receipt_footer TEXT,

  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- USUARIOS
-- =====================================================

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  username VARCHAR(50) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,

  first_name VARCHAR(80),
  last_name VARCHAR(80),
  phone VARCHAR(30),
  email VARCHAR(120),

  role user_role NOT NULL,
  status user_status DEFAULT 'active',

  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- CATEGORÍAS
-- =====================================================

CREATE TABLE categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  name VARCHAR(100) NOT NULL,
  slug VARCHAR(120) UNIQUE NOT NULL,

  status generic_status DEFAULT 'active',

  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- PRODUCTOS
-- =====================================================

CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  category_id UUID REFERENCES categories(id),

  sku VARCHAR(60) UNIQUE,
  name VARCHAR(150) NOT NULL,
  description TEXT,

  price NUMERIC(12,2) NOT NULL CHECK (price >= 0),
  unit_cost NUMERIC(12,2) DEFAULT 0 CHECK (unit_cost >= 0),

  stock INT DEFAULT 0,
  min_stock INT DEFAULT 0,

  image_url TEXT,

  status generic_status DEFAULT 'active',

  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Índices útiles
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_status ON products(status);

-- =====================================================
-- MESAS
-- =====================================================

CREATE TABLE tables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  name VARCHAR(50) UNIQUE NOT NULL,
  capacity INT DEFAULT 2,

  status generic_status DEFAULT 'active'
);

-- =====================================================
-- SESIONES DE CAJA
-- =====================================================

CREATE TABLE register_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  opened_by UUID REFERENCES users(id),
  closed_by UUID REFERENCES users(id),

  opening_amount NUMERIC(12,2) NOT NULL CHECK (opening_amount >= 0),
  closing_amount NUMERIC(12,2),
  expected_amount NUMERIC(12,2),
  difference NUMERIC(12,2),

  status register_status DEFAULT 'open',

  opened_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  closed_at TIMESTAMPTZ
);

-- 🔥 Solo permite UNA caja abierta al mismo tiempo
CREATE UNIQUE INDEX idx_single_open_register
ON register_sessions (status)
WHERE status = 'open';

-- =====================================================
-- ÓRDENES
-- =====================================================

CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  user_id UUID REFERENCES users(id),
  register_session_id UUID REFERENCES register_sessions(id),
  table_id UUID REFERENCES tables(id),

  customer_name VARCHAR(100),

  subtotal NUMERIC(12,2) DEFAULT 0 CHECK (subtotal >= 0),
  tax NUMERIC(12,2) DEFAULT 0 CHECK (tax >= 0),
  total NUMERIC(12,2) DEFAULT 0 CHECK (total >= 0),

  notes TEXT,

  status order_status DEFAULT 'open',

  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  closed_at TIMESTAMPTZ
);

-- Índices para consultas rápidas
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- =====================================================
-- DETALLE DE ÓRDENES
-- =====================================================

CREATE TABLE order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  product_id UUID REFERENCES products(id),

  quantity INT NOT NULL CHECK (quantity > 0),

  base_price NUMERIC(12,2) NOT NULL CHECK (base_price >= 0),
  historical_cost NUMERIC(12,2) DEFAULT 0 CHECK (historical_cost >= 0),

  subtotal NUMERIC(12,2) NOT NULL CHECK (subtotal >= 0),

  notes TEXT
);

-- =====================================================
-- PAGOS
-- =====================================================

CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  order_id UUID REFERENCES orders(id),
  register_session_id UUID REFERENCES register_sessions(id),

  method payment_method NOT NULL,

  amount_paid NUMERIC(12,2) NOT NULL CHECK (amount_paid > 0),
  reference VARCHAR(100),

  -- opcional pero recomendado para futuro
  status VARCHAR(20) DEFAULT 'paid',

  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Índice para consultas por orden
CREATE INDEX idx_payments_order_id ON payments(order_id);