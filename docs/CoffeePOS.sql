-- =====================================================
-- COFFEEPOS v1.0 FINAL (PostgreSQL PRO Edition)
-- Enfoque: Cafeterías / POS pequeños negocios
-- Escalable, limpio, producción real
-- =====================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =====================================================
-- ENUMS
-- =====================================================

CREATE TYPE user_role AS ENUM (
  'admin',
  'manager',
  'cashier',
  'barista'
);

CREATE TYPE user_status AS ENUM (
  'active',
  'inactive',
  'suspended',
  'terminated'
);

CREATE TYPE generic_status AS ENUM (
  'active',
  'inactive',
  'archived'
);

CREATE TYPE order_status AS ENUM (
  'open',
  'preparing',
  'ready',
  'paid',
  'cancelled'
);

CREATE TYPE payment_method AS ENUM (
  'cash',
  'card',
  'transfer'
);

CREATE TYPE register_status AS ENUM (
  'open',
  'closed'
);

CREATE TYPE movement_type AS ENUM (
  'income',
  'expense'
);

-- =====================================================
-- STORE SETTINGS
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

  currency VARCHAR(10) DEFAULT 'COP',
  language VARCHAR(10) DEFAULT 'es-CO',
  timezone VARCHAR(60) DEFAULT 'America/Bogota',
  country_code VARCHAR(5) DEFAULT 'CO',

  tax_percentage NUMERIC(5,2) DEFAULT 19.00,

  invoice_prefix VARCHAR(20) DEFAULT 'FAC',
  next_invoice_number INT DEFAULT 1,

  receipt_footer TEXT,

  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- USERS
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
-- CATEGORIES
-- =====================================================

CREATE TABLE categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  name VARCHAR(100) NOT NULL,
  slug VARCHAR(120) UNIQUE NOT NULL,

  status generic_status DEFAULT 'active',

  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- PRODUCTS
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

-- =====================================================
-- MODIFIERS
-- =====================================================

CREATE TABLE modifiers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  group_name VARCHAR(100) NOT NULL DEFAULT 'General',
  name VARCHAR(100) NOT NULL,
  price_adjustment NUMERIC(12,2) DEFAULT 0 NOT NULL,

  status generic_status DEFAULT 'active'
  
);

-- =====================================================
-- PRODUCT <-> MODIFIERS
-- =====================================================

CREATE TABLE product_modifiers (
  product_id UUID REFERENCES products(id) ON DELETE CASCADE,
  modifier_id UUID REFERENCES modifiers(id) ON DELETE CASCADE,

  PRIMARY KEY (product_id, modifier_id)
);

-- =====================================================
-- TABLES (Mesas físicas)
-- =====================================================

CREATE TABLE tables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  name VARCHAR(50) UNIQUE NOT NULL,
  capacity INT DEFAULT 2,

  status generic_status DEFAULT 'active'
);

-- =====================================================
-- REGISTER SESSIONS (Caja)
-- =====================================================

CREATE TABLE register_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  opened_by UUID REFERENCES users(id),
  closed_by UUID REFERENCES users(id),

  opening_amount NUMERIC(12,2) NOT NULL,
  closing_amount NUMERIC(12,2),
  expected_amount NUMERIC(12,2),
  difference NUMERIC(12,2),

  status register_status DEFAULT 'open',

  opened_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  closed_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_single_open_register
ON register_sessions(status)
WHERE status = 'open';

-- =====================================================
-- ORDERS
-- =====================================================

CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  user_id UUID REFERENCES users(id),
  register_session_id UUID REFERENCES register_sessions(id),

  table_id UUID REFERENCES tables(id),

  customer_name VARCHAR(100),

  subtotal NUMERIC(12,2) DEFAULT 0,
  tax NUMERIC(12,2) DEFAULT 0,
  total NUMERIC(12,2) DEFAULT 0,

  notes TEXT,

  status order_status DEFAULT 'open',

  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  closed_at TIMESTAMPTZ
);

-- =====================================================
-- ORDER ITEMS
-- =====================================================

CREATE TABLE order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  product_id UUID REFERENCES products(id),

  quantity INT NOT NULL CHECK (quantity > 0),

  base_price NUMERIC(12,2) NOT NULL,
  historical_cost NUMERIC(12,2) DEFAULT 0,

  subtotal NUMERIC(12,2) NOT NULL,

  notes TEXT
);

-- =====================================================
-- ORDER ITEM MODIFIERS
-- =====================================================

CREATE TABLE order_item_modifiers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  order_item_id UUID REFERENCES order_items(id) ON DELETE CASCADE,
  modifier_id UUID REFERENCES modifiers(id),

  historical_price_adjustment NUMERIC(12,2) NOT NULL
);

-- =====================================================
-- PAYMENTS
-- =====================================================

CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  order_id UUID REFERENCES orders(id),
  register_session_id UUID REFERENCES register_sessions(id),

  method payment_method NOT NULL,

  amount_paid NUMERIC(12,2) NOT NULL CHECK (amount_paid > 0),
  reference VARCHAR(100),

  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- CASH MOVEMENTS
-- =====================================================

CREATE TABLE cash_movements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  register_session_id UUID REFERENCES register_sessions(id),

  type movement_type NOT NULL,
  amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),

  reason TEXT NOT NULL,

  created_by UUID REFERENCES users(id),

  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- ACCOUNTING LEDGER (Opcional avanzado)
-- =====================================================

CREATE TABLE accounting_ledger (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  transaction_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

  account_name VARCHAR(100) NOT NULL,
  description TEXT NOT NULL,

  debit NUMERIC(12,2) DEFAULT 0 CHECK (debit >= 0),
  credit NUMERIC(12,2) DEFAULT 0 CHECK (credit >= 0),

  reference_id UUID,
  reference_type VARCHAR(50),

  created_by UUID REFERENCES users(id)
);

-- =====================================================
-- INDEXES IMPORTANTES
-- =====================================================

CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

CREATE INDEX idx_payments_order_id ON payments(order_id);

CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_status ON products(status);

CREATE INDEX idx_cash_movements_session ON cash_movements(register_session_id);