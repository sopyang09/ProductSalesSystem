
import sqlite3
import os

# Get the main ProductSalesSystem folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Database location
DATABASE_PATH = os.path.join(BASE_DIR, "products.db")


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def create_table():
    connection = get_connection()

    # Products table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)

    # Sales table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total REAL NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_table()
    print("Database tables created successfully!")

if __name__ == "__main__":
    create_table()

    connection = get_connection()

    products = connection.execute(
        "SELECT * FROM products"
    ).fetchall()

    print("PRODUCTS FOUND:", len(products))

    for product in products:
        print(dict(product))

    connection.close()
