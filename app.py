
from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from database.db import get_connection, create_table
from collections import deque

app = Flask(__name__)
app.secret_key = "product_sales_secret_key"

# =====================================
# DATA STRUCTURES
# =====================================

# Queue data structure (FIFO)
sales_queue = deque()

# List data structure is used in the Products page

# =====================================
# ADMIN LOGIN CREDENTIALS
# =====================================

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# =====================================
# LOGIN PROTECTION
# =====================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "logged_in" not in session:
            flash("Please login first.")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# Create database tables
create_table()


# =====================================
# ADMIN LOGIN
# =====================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if session.get("logged_in"):
        return redirect(url_for("home"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:

            session["logged_in"] = True

            flash("Login successful!")
            return redirect(url_for("home"))

        else:
            flash("Invalid username or password.")

    return render_template("login.html")


# =====================================
# ADMIN LOGOUT
# =====================================

# =====================================
# ADMIN PROFILE
# =====================================

@app.route("/admin-profile")
@login_required
def admin_profile():

    return render_template("admin_profile.html")


@app.route("/logout")
def logout():

    session.clear()

    flash("You have successfully logged out.")

    return redirect(url_for("login"))


# =====================================
# DASHBOARD
# =====================================

@app.route("/")
@login_required
def home():

    connection = get_connection()

    total_products = connection.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    total_sales = connection.execute(
        "SELECT COALESCE(SUM(total), 0) FROM sales"
    ).fetchone()[0]

    total_transactions = connection.execute(
        "SELECT COUNT(*) FROM sales"
    ).fetchone()[0]

    low_stock = connection.execute(
        "SELECT COUNT(*) FROM products WHERE stock <= 5"
    ).fetchone()[0]

    total_stock = connection.execute(
        "SELECT COALESCE(SUM(stock), 0) FROM products"
    ).fetchone()[0]

    connection.close()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_sales=total_sales,
        total_transactions=total_transactions,
        low_stock=low_stock,
        total_stock=total_stock
    )


# =====================================
# VIEW AND SEARCH PRODUCTS
# =====================================

@app.route("/products")
@login_required
def products():

    search = request.args.get("search", "")

    connection = get_connection()

    product_list = connection.execute(
        """
        SELECT * FROM products
        WHERE product_name LIKE ?
        ORDER BY id DESC
        """,
        ('%' + search + '%',)
    ).fetchall()

    # List data structure
    product_list = list(product_list)

    connection.close()

    return render_template(
        "products.html",
        products=product_list,
        search=search
    )


# =====================================
# ADD PRODUCT
# =====================================

@app.route("/products/add", methods=["GET", "POST"])
@login_required
def add_product():

    if request.method == "POST":

        name = request.form.get("product_name", "").strip()

        try:
            price = float(request.form.get("price", ""))
            stock = int(request.form.get("stock", ""))

        except ValueError:
            flash("Please enter a valid price and stock.")
            return redirect(url_for("add_product"))

        if not name:
            flash("Product name is required.")
            return redirect(url_for("add_product"))

        if price < 0 or stock < 0:
            flash("Price and stock cannot be negative.")
            return redirect(url_for("add_product"))

        connection = get_connection()

        connection.execute(
            """
            INSERT INTO products (product_name, price, stock)
            VALUES (?, ?, ?)
            """,
            (name, price, stock)
        )

        connection.commit()
        connection.close()

        flash("Product added successfully!")
        return redirect(url_for("products"))

    return render_template(
        "product_form.html",
        title="Add New Product",
        product=None
    )


# =====================================
# UPDATE PRODUCT
# =====================================

@app.route("/products/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_product(id):

    connection = get_connection()

    product = connection.execute(
        "SELECT * FROM products WHERE id = ?",
        (id,)
    ).fetchone()

    if product is None:
        connection.close()
        flash("Product not found.")
        return redirect(url_for("products"))

    if request.method == "POST":

        name = request.form.get("product_name", "").strip()

        try:
            price = float(request.form.get("price", ""))
            stock = int(request.form.get("stock", ""))

        except ValueError:
            connection.close()
            flash("Please enter a valid price and stock.")
            return redirect(url_for("edit_product", id=id))

        if not name or price < 0 or stock < 0:
            connection.close()
            flash("Please enter valid product information.")
            return redirect(url_for("edit_product", id=id))

        connection.execute(
            """
            UPDATE products
            SET product_name = ?, price = ?, stock = ?
            WHERE id = ?
            """,
            (name, price, stock, id)
        )

        connection.commit()
        connection.close()

        flash("Product updated successfully!")
        return redirect(url_for("products"))

    connection.close()

    return render_template(
        "product_form.html",
        title="Edit Product",
        product=product
    )


# =====================================
# DELETE PRODUCT
# =====================================

@app.route("/products/delete/<int:id>", methods=["POST"])
@login_required
def delete_product(id):

    connection = get_connection()

    product = connection.execute(
        "SELECT * FROM products WHERE id = ?",
        (id,)
    ).fetchone()

    if product is None:
        connection.close()
        flash("Product not found.")
        return redirect(url_for("products"))

    connection.execute(
        "DELETE FROM products WHERE id = ?",
        (id,)
    )

    connection.commit()
    connection.close()

    flash("Product deleted successfully!")
    return redirect(url_for("products"))


# =====================================
# PROCESS SALES
# =====================================

@app.route("/sales", methods=["GET", "POST"])
@login_required
def sales():

    connection = get_connection()

    if request.method == "POST":

        product_id = request.form.get("product_id")

        try:
            quantity = int(request.form.get("quantity", ""))

        except ValueError:
            connection.close()
            flash("Please enter a valid quantity.")
            return redirect(url_for("sales"))

        if quantity <= 0:
            connection.close()
            flash("Quantity must be greater than zero.")
            return redirect(url_for("sales"))

        product = connection.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product is None:
            connection.close()
            flash("Product not found.")
            return redirect(url_for("sales"))

        if quantity > product["stock"]:
            connection.close()
            flash("Not enough stock available.")
            return redirect(url_for("sales"))

        # Add sale request to Queue
        sales_queue.append((product_id, quantity))

        # Process the first sale in the Queue
        sale_product_id, sale_quantity = sales_queue.popleft()

        total = product["price"] * sale_quantity

        connection.execute(
            """
            UPDATE products
            SET stock = stock - ?
            WHERE id = ?
            """,
            (sale_quantity, sale_product_id)
        )

        connection.execute(
            """
            INSERT INTO sales
            (product_id, product_name, quantity, total)
            VALUES (?, ?, ?, ?)
            """,
            (
                sale_product_id,
                product["product_name"],
                sale_quantity,
                total
            )
        )

        connection.commit()
        connection.close()

        flash("Sale processed successfully!")
        return redirect(url_for("sales"))

    product_list = connection.execute(
        "SELECT * FROM products ORDER BY product_name"
    ).fetchall()

    connection.close()

    return render_template(
        "sales.html",
        products=product_list
    )


# =====================================
# SALES HISTORY
# =====================================

@app.route("/sales-history")
@login_required
def sales_history():

    connection = get_connection()

    sales_list = connection.execute(
        """
        SELECT * FROM sales
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "sales_history.html",
        sales=sales_list
    )


# =====================================
# RUN APPLICATION
# =====================================

if __name__ == "__main__":
    app.run(debug=True)
