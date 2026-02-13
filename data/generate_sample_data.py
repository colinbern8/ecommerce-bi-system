"""
Generate sample e-commerce data using Faker and insert via DatabaseManager.
Creates customers, products, orders, order_items, and support_tickets with progress bars.
"""

import random
import sqlite3
import sys
from pathlib import Path

from faker import Faker
from tqdm import tqdm

# Project root and src on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC))

from database import DatabaseManager

# Targets
NUM_CUSTOMERS = 5000
NUM_PRODUCTS = 2000
NUM_ORDERS = 50000
NUM_ORDER_ITEMS = 100000
NUM_TICKETS = 3000

CATEGORIES = [
    ("Electronics", 0.30),
    ("Apparel", 0.25),
    ("Home & Garden", 0.20),
    ("Sports", 0.15),
    ("Books", 0.10),
]
ORDER_STATUSES = [("Completed", 0.70), ("Cancelled", 0.20), ("Returned", 0.10)]
PAYMENT_METHODS = ["Credit Card", "Debit Card", "PayPal", "Bank Transfer", "Cash"]
RESOLUTION_STATUSES = ["Resolved", "Unresolved"]
SEGMENTS = ["Standard", "Premium", "Budget"]


def weighted_choice(choices):
    r = random.random()
    for item, weight in choices:
        r -= weight
        if r <= 0:
            return item
    return choices[-1][0]


def main() -> None:
    fake = Faker()
    Faker.seed(42)
    random.seed(42)

    config_path = PROJECT_ROOT / "config" / "config.yaml"
    db = DatabaseManager(config_path=str(config_path))

    db_path = PROJECT_ROOT / "data" / "ecommerce.db"
    schema_path = PROJECT_ROOT / "sql" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()
    schema_sqlite = (
        schema.replace("SERIAL", "INTEGER")
        .replace("VARCHAR(255)", "TEXT")
        .replace("VARCHAR(100)", "TEXT")
        .replace("VARCHAR(50)", "TEXT")
        .replace("DECIMAL(10, 2)", "REAL")
        .replace("ON DELETE CASCADE", "")
        .replace("CASCADE", "")
    )

    engine = db.engine
    conn = engine.raw_connection()
    cursor = conn.cursor()
    for stmt in schema_sqlite.split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                cursor.execute(stmt)
            except Exception:
                pass
    conn.commit()

    print("Generating customers...")
    customers = []
    seen_emails = set()
    for _ in tqdm(range(NUM_CUSTOMERS), desc="Customers"):
        while True:
            email = fake.unique.email()
            if email not in seen_emails:
                seen_emails.add(email)
                break
        customers.append(
            (
                email,
                fake.first_name(),
                fake.last_name(),
                fake.date_between(start_date="-2y", end_date="today").isoformat(),
                fake.country_code(),
                random.choice(SEGMENTS),
            )
        )

    batch_size = 500
    for i in tqdm(range(0, len(customers), batch_size), desc="Insert customers"):
        batch = customers[i : i + batch_size]
        for c in batch:
            cursor.execute(
                "INSERT INTO customers (email, first_name, last_name, registration_date, country, customer_segment) VALUES (?,?,?,?,?,?)",
                c,
            )
    conn.commit()

    print("Generating products...")
    category_list = []
    for cat, weight in CATEGORIES:
        n = int(NUM_PRODUCTS * weight)
        category_list.extend([cat] * n)
    while len(category_list) < NUM_PRODUCTS:
        category_list.append(weighted_choice(CATEGORIES))
    category_list = category_list[:NUM_PRODUCTS]
    random.shuffle(category_list)
    products = []
    for i in tqdm(range(NUM_PRODUCTS), desc="Products"):
        cat = category_list[i]
        unit_cost = round(random.uniform(5, 200), 2)
        unit_price = round(unit_cost * random.uniform(1.2, 2.5), 2)
        products.append(
            (
                fake.catch_phrase(),
                cat,
                fake.word() if random.random() > 0.5 else None,
                unit_cost,
                unit_price,
                random.randint(1, 100) if random.random() > 0.3 else None,
            )
        )

    for i in tqdm(range(0, len(products), batch_size), desc="Insert products"):
        for p in products[i : i + batch_size]:
            cursor.execute(
                "INSERT INTO products (product_name, category, subcategory, unit_cost, unit_price, supplier_id) VALUES (?,?,?,?,?,?)",
                p,
            )
    conn.commit()

    print("Generating orders...")
    customer_ids = [r[0] for r in cursor.execute("SELECT customer_id FROM customers").fetchall()]
    orders = []
    for _ in tqdm(range(NUM_ORDERS), desc="Orders"):
        orders.append(
            (
                random.choice(customer_ids),
                fake.date_between(start_date="-12 months", end_date="today").isoformat(),
                weighted_choice(ORDER_STATUSES),
                round(random.uniform(0, 15), 2) if random.random() > 0.3 else None,
                round(random.uniform(0, 20), 2) if random.random() > 0.6 else 0.0,
                random.choice(PAYMENT_METHODS),
            )
        )
    for i in tqdm(range(0, len(orders), batch_size), desc="Insert orders"):
        for o in orders[i : i + batch_size]:
            cursor.execute(
                "INSERT INTO orders (customer_id, order_date, order_status, shipping_cost, discount_amount, payment_method) VALUES (?,?,?,?,?,?)",
                o,
            )
    conn.commit()

    print("Generating order_items...")
    order_ids = [r[0] for r in cursor.execute("SELECT order_id FROM orders").fetchall()]
    product_rows = cursor.execute("SELECT product_id, unit_price, unit_cost FROM products").fetchall()
    order_items = []
    for _ in tqdm(range(NUM_ORDER_ITEMS), desc="Order items"):
        oid = random.choice(order_ids)
        pid, u_price, u_cost = random.choice(product_rows)
        order_items.append((oid, pid, random.randint(1, 5), u_price, u_cost))
    for i in tqdm(range(0, len(order_items), batch_size), desc="Insert order_items"):
        for oi in order_items[i : i + batch_size]:
            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price, unit_cost) VALUES (?,?,?,?,?)",
                oi,
            )
    conn.commit()

    print("Generating support_tickets...")
    tickets = []
    for _ in tqdm(range(NUM_TICKETS), desc="Tickets"):
        tickets.append(
            (
                random.choice(customer_ids),
                fake.date_between(start_date="-1y", end_date="today").isoformat(),
                fake.sentence(nb_words=3),
                random.choice(RESOLUTION_STATUSES),
            )
        )
    for i in tqdm(range(0, len(tickets), batch_size), desc="Insert tickets"):
        for t in tickets[i : i + batch_size]:
            cursor.execute(
                "INSERT INTO support_tickets (customer_id, ticket_date, issue_type, resolution_status) VALUES (?,?,?,?)",
                t,
            )
    conn.commit()
    conn.close()
    db.close()

    # Summary
    conn = sqlite3.connect(str(db_path))
    print("\n--- Summary ---")
    for table in ["customers", "products", "orders", "order_items", "support_tickets"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {n}")
    conn.close()
    print("Sample data generation complete.")


if __name__ == "__main__":
    main()
