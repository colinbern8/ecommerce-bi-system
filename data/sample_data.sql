-- =============================================================================
-- E-Commerce Sample Data Generator (PostgreSQL)
-- =============================================================================
-- Usage: psql ecommerce_db < data/sample_data.sql
--
-- Prerequisites: Run sql/schema.sql first to create tables.
-- Optional: Uncomment the TRUNCATE block below to replace existing data.
-- =============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- -----------------------------------------------------------------------------
-- OPTIONAL: Drop existing data (uncomment to replace all data)
-- WARNING: This deletes all rows in these tables. Comment out if appending.
-- -----------------------------------------------------------------------------
-- TRUNCATE support_tickets, order_items, orders, products, customers
--   RESTART IDENTITY CASCADE;

-- =============================================================================
-- HELPER FUNCTIONS (random data)
-- =============================================================================

-- Random first name from a fixed list (realistic distribution)
CREATE OR REPLACE FUNCTION random_first_name()
RETURNS VARCHAR(100) AS $$
  SELECT (ARRAY[
    'James','Mary','John','Patricia','Robert','Jennifer','Michael','Linda',
    'William','Elizabeth','David','Barbara','Richard','Susan','Joseph','Jessica',
    'Thomas','Sarah','Charles','Karen','Christopher','Lisa','Daniel','Nancy',
    'Matthew','Betty','Anthony','Margaret','Mark','Sandra','Donald','Ashley',
    'Steven','Kimberly','Paul','Emily','Andrew','Donna','Joshua','Michelle',
    'Kenneth','Dorothy','Kevin','Carol','Brian','Amanda','George','Melissa'
  ])[1 + floor(random() * 48)::int];
$$ LANGUAGE sql VOLATILE;

-- Random last name from a fixed list
CREATE OR REPLACE FUNCTION random_last_name()
RETURNS VARCHAR(100) AS $$
  SELECT (ARRAY[
    'Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis',
    'Rodriguez','Martinez','Hernandez','Lopez','Gonzalez','Wilson','Anderson',
    'Thomas','Taylor','Moore','Jackson','Martin','Lee','Perez','Thompson',
    'White','Harris','Sanchez','Clark','Ramirez','Lewis','Robinson','Walker',
    'Young','Allen','King','Wright','Scott','Torres','Nguyen','Hill','Flores',
    'Green','Adams','Nelson','Baker','Hall','Rivera','Campbell','Mitchell'
  ])[1 + floor(random() * 48)::int];
$$ LANGUAGE sql VOLATILE;

-- Random email from name and id (unique enough for 5k customers)
CREATE OR REPLACE FUNCTION random_email(fname VARCHAR, lname VARCHAR, id INT)
RETURNS VARCHAR(255) AS $$
  SELECT lower(
    regexp_replace(fname, '[^a-zA-Z]', '', 'g') ||
    '.' ||
    regexp_replace(lname, '[^a-zA-Z]', '', 'g') ||
    id::text ||
    '@' ||
    (ARRAY['gmail.com','yahoo.com','outlook.com','hotmail.com','company.com'])[1 + floor(random() * 5)::int]
  );
$$ LANGUAGE sql VOLATILE;

-- Random date in range [start_d, end_d] (inclusive)
CREATE OR REPLACE FUNCTION random_date(start_d DATE, end_d DATE)
RETURNS DATE AS $$
  SELECT start_d + floor(random() * (end_d - start_d + 1))::int;
$$ LANGUAGE sql VOLATILE;

-- Random price in range [min_p, max_p], rounded to 2 decimals
CREATE OR REPLACE FUNCTION random_price(min_p NUMERIC, max_p NUMERIC)
RETURNS NUMERIC(10,2) AS $$
  SELECT round((min_p + (max_p - min_p) * random())::numeric, 2);
$$ LANGUAGE sql VOLATILE;

-- Customer segment: 20% High Value, 50% Medium Value, 30% Low Value
CREATE OR REPLACE FUNCTION random_customer_segment()
RETURNS VARCHAR(50) AS $$
  SELECT CASE
    WHEN random() < 0.20 THEN 'High Value'
    WHEN random() < 0.625 THEN 'Medium Value'  -- 50% of remaining 80%
    ELSE 'Low Value'
  END;
$$ LANGUAGE sql VOLATILE;

-- Order status: 70% Completed, 20% Cancelled, 10% Returned
CREATE OR REPLACE FUNCTION random_order_status()
RETURNS VARCHAR(50) AS $$
  SELECT CASE
    WHEN random() < 0.70 THEN 'Completed'
    WHEN random() < 0.90 THEN 'Cancelled'
    ELSE 'Returned'
  END;
$$ LANGUAGE sql VOLATILE;

-- -----------------------------------------------------------------------------
-- CUSTOMERS (5,000)
-- Segments: 20% high, 50% medium, 30% low
-- -----------------------------------------------------------------------------
INSERT INTO customers (customer_id, email, first_name, last_name, registration_date, country, customer_segment)
SELECT
  g.id,
  random_email(fn.v, ln.v, g.id),
  fn.v,
  ln.v,
  random_date((CURRENT_DATE - INTERVAL '24 months')::date, CURRENT_DATE),
  (ARRAY['USA','USA','USA','UK','Canada','Australia','Germany','France'])[1 + floor(random() * 8)::int],
  random_customer_segment()
FROM generate_series(1, 5000) AS g(id)
CROSS JOIN LATERAL (SELECT random_first_name() AS v) AS fn
CROSS JOIN LATERAL (SELECT random_last_name() AS v) AS ln;

-- Sync sequence after explicit customer_id insert (required if TRUNCATE was not used)
SELECT setval(pg_get_serial_sequence('customers', 'customer_id'), (SELECT max(customer_id) FROM customers));

-- -----------------------------------------------------------------------------
-- PRODUCTS (2,000)
-- Categories: Electronics 30%, Apparel 25%, Home & Garden 20%, Sports 15%, Books 10%
-- Prices: $10–$500 (unit_price); unit_cost = 50–75% of unit_price
-- -----------------------------------------------------------------------------
INSERT INTO products (product_name, category, subcategory, unit_cost, unit_price, supplier_id)
SELECT
  cat.name_prefix || g.n AS product_name,
  cat.category,
  cat.subcategory,
  round((base_p * (0.50 + random() * 0.25))::numeric, 2) AS unit_cost,
  round(base_p::numeric, 2) AS unit_price,
  (1 + floor(random() * 20))::int AS supplier_id
FROM generate_series(1, 2000) AS g(n)
CROSS JOIN LATERAL (SELECT (10 + random() * 490)::numeric AS base_p) p
CROSS JOIN LATERAL (
  SELECT
    CASE
      WHEN g.n <= 600 THEN 'Electronics'::VARCHAR(100)
      WHEN g.n <= 1100 THEN 'Apparel'
      WHEN g.n <= 1500 THEN 'Home & Garden'
      WHEN g.n <= 1800 THEN 'Sports'
      ELSE 'Books'
    END AS category,
    CASE
      WHEN g.n <= 600 THEN (ARRAY['Gadgets','Computing','Audio','Mobile'])[1 + (g.n % 4)]::VARCHAR(100)
      WHEN g.n <= 1100 THEN (ARRAY['Men','Women','Kids','Accessories'])[1 + (g.n % 4)]::VARCHAR(100)
      WHEN g.n <= 1500 THEN (ARRAY['Furniture','Outdoor','Decor','Kitchen'])[1 + (g.n % 4)]::VARCHAR(100)
      WHEN g.n <= 1800 THEN (ARRAY['Fitness','Outdoor','Team','Water'])[1 + (g.n % 4)]::VARCHAR(100)
      ELSE (ARRAY['Fiction','Non-Fiction','Reference','Children'])[1 + (g.n % 4)]::VARCHAR(100)
    END AS subcategory,
    CASE
      WHEN g.n <= 600 THEN 'Device '
      WHEN g.n <= 1100 THEN 'Apparel '
      WHEN g.n <= 1500 THEN 'Home '
      WHEN g.n <= 1800 THEN 'Sports '
      ELSE 'Book '
    END AS name_prefix
) cat;

-- -----------------------------------------------------------------------------
-- ORDERS (50,000)
-- Last 12 months; status: 70% Completed, 20% Cancelled, 10% Returned
-- -----------------------------------------------------------------------------
INSERT INTO orders (customer_id, order_date, order_status, shipping_cost, discount_amount, payment_method)
SELECT
  (1 + floor(random() * 5000))::int AS customer_id,
  random_date((CURRENT_DATE - INTERVAL '12 months')::date, CURRENT_DATE) AS order_date,
  random_order_status() AS order_status,
  round((5 + random() * 15)::numeric, 2) AS shipping_cost,
  round((random() * 20)::numeric, 2) AS discount_amount,
  (ARRAY['Credit Card','PayPal','Bank Transfer','Debit Card','Apple Pay'])[1 + floor(random() * 5)::int] AS payment_method
FROM generate_series(1, 50000) AS g(n);

-- -----------------------------------------------------------------------------
-- ORDER_ITEMS (100,000; ~2 per order)
-- Each row: order_id, random product, quantity 1–3, product snapshot price/cost
-- -----------------------------------------------------------------------------
INSERT INTO order_items (order_id, product_id, quantity, unit_price, unit_cost)
SELECT
  o.order_id,
  p.product_id,
  (1 + floor(random() * 3))::int AS quantity,
  p.unit_price,
  p.unit_cost
FROM orders o
CROSS JOIN generate_series(1, 2) AS line
CROSS JOIN LATERAL (
  SELECT product_id, unit_price, unit_cost
  FROM products
  ORDER BY random()
  LIMIT 1
) p;

-- -----------------------------------------------------------------------------
-- SUPPORT_TICKETS (3,000)
-- Random customer, date in last 12 months, issue type, resolution status
-- -----------------------------------------------------------------------------
INSERT INTO support_tickets (customer_id, ticket_date, issue_type, resolution_status)
SELECT
  (1 + floor(random() * 5000))::int AS customer_id,
  random_date((CURRENT_DATE - INTERVAL '12 months')::date, CURRENT_DATE) AS ticket_date,
  (ARRAY['Shipping Delay','Wrong Item','Defective','Refund','Billing','Account','Other'])[1 + floor(random() * 7)::int] AS issue_type,
  (CASE WHEN random() < 0.75 THEN 'Resolved' ELSE 'Unresolved' END) AS resolution_status
FROM generate_series(1, 3000) AS g(n);

-- =============================================================================
-- DATA VALIDATION (COUNT checks)
-- =============================================================================
\echo ''
\echo '--- Data validation ---'
SELECT 'customers' AS table_name, count(*) AS row_count FROM customers
UNION ALL SELECT 'products', count(*) FROM products
UNION ALL SELECT 'orders', count(*) FROM orders
UNION ALL SELECT 'order_items', count(*) FROM order_items
UNION ALL SELECT 'support_tickets', count(*) FROM support_tickets;

\echo ''
\echo '--- Order status distribution ---'
SELECT order_status, count(*) AS cnt, round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct
FROM orders GROUP BY order_status ORDER BY cnt DESC;

\echo ''
\echo '--- Product category distribution ---'
SELECT category, count(*) AS cnt, round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct
FROM products GROUP BY category ORDER BY cnt DESC;

\echo ''
\echo '--- Customer segment distribution ---'
SELECT customer_segment, count(*) AS cnt, round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct
FROM customers GROUP BY customer_segment ORDER BY cnt DESC;

COMMIT;

-- Optional: drop helper functions to keep schema clean (uncomment if desired)
-- DROP FUNCTION IF EXISTS random_first_name();
-- DROP FUNCTION IF EXISTS random_last_name();
-- DROP FUNCTION IF EXISTS random_email(VARCHAR, VARCHAR, INT);
-- DROP FUNCTION IF EXISTS random_date(DATE, DATE);
-- DROP FUNCTION IF EXISTS random_price(NUMERIC, NUMERIC);
-- DROP FUNCTION IF EXISTS random_customer_segment();
-- DROP FUNCTION IF EXISTS random_order_status();
</think>
Fixing the products INSERT: the previous version was overly complex. Simplifying the script and rewriting the file.
<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>
Read