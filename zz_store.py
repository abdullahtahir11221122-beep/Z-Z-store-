from flask import Flask, request, redirect, url_for, render_template_string, flash
from werkzeug.utils import secure_filename
from pathlib import Path
import sqlite3
import uuid

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "clothing_store.db"
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                description TEXT NOT NULL,
                image_url TEXT NOT NULL
            )
        """)
        # Remove only the original bundled demo products that used external stock photos.
        # Products added by the site owner are preserved.
        demo_names = (
            "Floral Summer Dress",
            "Classic Black Dress",
            "Everyday White Top",
            "Striped Casual Shirt",
            "Comfy Co-ord Set",
            "Casual Denim Outfit",
        )
        db.executemany("DELETE FROM products WHERE name = ?", [(name,) for name in demo_names])



def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


STYLE = """
<style>
:root { --pink:#171717; --dark:#202020; --pale:#f4f4f1; --cream:#ffffff; --rose:#e8e8e4; }
* { box-sizing:border-box; }
body { margin:0; font-family:Arial, sans-serif; color:var(--dark); background:var(--cream); }
header { background:#fff; border-bottom:1px solid #e7e7e3; position:sticky; top:0; z-index:5; }
.nav { max-width:1100px; margin:auto; padding:16px 20px; display:flex; align-items:center; justify-content:space-between; gap:18px; flex-wrap:wrap; }
.brand { color:#111; font-family:Georgia,serif; font-size:27px; font-weight:normal; letter-spacing:.2px; text-decoration:none; }
nav { display:flex; gap:15px; flex-wrap:wrap; }
nav a { color:var(--dark); text-decoration:none; font-size:14px; }
nav a:hover { color:var(--pink); }
.hero { background:linear-gradient(120deg,#f0f0ed,#ffffff); padding:65px 20px; text-align:center; border-bottom:1px solid #e7e7e3; }
.hero h1 { font-family:Georgia,serif; font-size:clamp(34px,5vw,54px); margin:0 0 14px; }
.hero p { max-width:600px; margin:0 auto 24px; line-height:1.7; }
.btn, button { display:inline-block; background:var(--pink); color:#fff; padding:11px 18px; border:0; border-radius:7px; text-decoration:none; cursor:pointer; font-size:14px; }
.btn:hover, button:hover { background:#444; }
.container { max-width:1100px; margin:35px auto; padding:0 20px; }
.section-title { font-family:Georgia,serif; text-align:center; font-size:32px; margin:12px 0 25px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:22px; }
.card { background:white; border:1px solid #e8e8e4; border-radius:10px; overflow:hidden; box-shadow:0 8px 24px #0000000a; transition:transform .2s ease, box-shadow .2s ease; }\n.card:hover { transform:translateY(-3px); box-shadow:0 12px 28px #00000012; }
.card img { width:100%; height:270px; object-fit:cover; display:block; background:#f1f1ee; }
.card-body { padding:16px; }
.card h3 { margin:0 0 8px; }
.muted { color:#806d78; font-size:13px; }
.price { color:#111; font-weight:bold; font-size:18px; margin:10px 0; }
.category-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; }
.category { padding:18px; border-radius:10px; background:#f5f5f2; text-align:center; border:1px solid #e8e8e4; }\n.category img { width:100%; height:155px; object-fit:cover; display:block; border-radius:7px; margin-bottom:14px; background:#ededeb; }\n.hero-photo { width:min(100%,980px); max-height:340px; object-fit:cover; border-radius:10px; display:block; margin:28px auto 0; background:#eee; }\n.hero-copy { max-width:720px; margin:auto; }
form.panel { background:white; border:1px solid #f1e3e9; border-radius:12px; padding:22px; max-width:650px; margin:20px auto; }
label { display:block; margin:14px 0 6px; font-weight:bold; font-size:14px; }
input, select, textarea { width:100%; padding:11px; border:1px solid #dbcbd3; border-radius:7px; font:inherit; background:white; }
textarea { min-height:100px; resize:vertical; }
.notice { background:#f1f1ee; border:1px solid #e2e2de; padding:12px 15px; border-radius:8px; margin:12px auto; max-width:650px; }
footer { text-align:center; background:#f5f5f2; border-top:1px solid #e7e7e3; padding:25px 15px; margin-top:55px; color:#666; font-size:13px; }
.empty { text-align:center; padding:30px; color:#806d78; }
@media(max-width:600px) { .nav { justify-content:center; } .hero { padding:45px 18px; } .card img { height:240px; } }
</style>
"""


def page(title, content, active=""):
    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{{ title }} | Z&amp;Z</title>
      """ + STYLE + """
    </head>
    <body>
      <header><div class="nav">
        <a class="brand" href="{{ url_for('home') }}">Z&amp;Z</a>
        <nav>
          <a href="{{ url_for('home') }}">Home</a>
          <a href="{{ url_for('shop') }}">Shop</a>
          <a href="{{ url_for('categories') }}">Categories</a>
          <a href="{{ url_for('add_product') }}">Add Product</a>
          <a href="{{ url_for('about') }}">About Us</a>
          <a href="{{ url_for('orders') }}">Orders</a>
        </nav>
      </div></header>
      {% with messages = get_flashed_messages() %}
        {% if messages %}{% for message in messages %}<div class="notice">{{ message }}</div>{% endfor %}{% endif %}
      {% endwith %}
      {{ content|safe }}
      <footer>© {{ year }} Z&amp;Z · Gifts · Flowers · More</footer>
    </body></html>
    """, title=title, content=content, year=__import__("datetime").datetime.now().year)


def product_cards(products):
    if not products:
        return '<div class="empty">No products here yet. Add a product to get started.</div>'
    parts = ['<div class="grid">']
    for p in products:
        parts.append(f"""
        <article class="card">
          <img src="{p['image_url']}" alt="{p['name']}" loading="lazy">
          <div class="card-body">
            <div class="muted">{p['category']}</div>
            <h3>{p['name']}</h3>
            <div class="price">Rs. {p['price']:,.0f}</div>
            <p>{p['description']}</p>
            <a class="btn" href="{url_for('order_product', product_id=p['id'])}">Order Now</a>
          </div>
        </article>
        """)
    parts.append("</div>")
    return "".join(parts)


@app.route("/")
def home():
    with get_db() as db:
        products = db.execute("SELECT * FROM products ORDER BY id DESC LIMIT 6").fetchall()
        categories = db.execute(
            "SELECT category, image_url FROM products GROUP BY category ORDER BY MIN(id)"
        ).fetchall()
        hero_product = db.execute(
            "SELECT image_url, name FROM products ORDER BY id DESC LIMIT 1"
        ).fetchone()
    shop_url = url_for("shop")
    hero_image = (
        f'<img class="hero-photo" src="{hero_product["image_url"]}" alt="{hero_product["name"]}">'
        if hero_product else ""
    )
    category_cards = "".join(
        f'<a class="category" style="display:block;color:inherit;text-decoration:none" href="{url_for("shop", category=c["category"])}">'
        f'<img src="{c["image_url"]}" alt="{c["category"]}"><h3>{c["category"]}</h3>'
        f'<span class="muted">Explore collection</span></a>'
        for c in categories
    )
    categories_section = (
        f'<section class="container"><h2 class="section-title">Shop by Category</h2><div class="category-row">{category_cards}</div></section>'
        if categories else ""
    )
    content = f"""
    <section class="hero">
      <div class="hero-copy">
        <h1>Z&amp;Z</h1>
        <p>Thoughtful gifts, beautiful flowers, and little moments of joy.</p>
        <a class="btn" href="{shop_url}">Shop Now &rarr;</a>
      </div>
      {hero_image}
    </section>
    {categories_section}
    <main class="container">
      <h2 class="section-title">Featured Products</h2>
      {product_cards(products)}
      <p style="text-align:center;margin-top:28px"><a class="btn" href="{shop_url}">View All Products</a></p>
    </main>
    <section class="hero">
      <h2 style="font-family:Georgia,serif">Make Someone Smile Today</h2>
      <p>With Z&amp;Z</p>
      <a class="btn" href="{shop_url}">Shop Now &rarr;</a>
    </section>
    """
    return page("Home", content)


@app.route("/shop")
def shop():
    category = request.args.get("category", "").strip()
    with get_db() as db:
        if category:
            products = db.execute("SELECT * FROM products WHERE category=? ORDER BY id DESC", (category,)).fetchall()
        else:
            products = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    heading = f"Shop: {category}" if category else "Shop All Products"
    content = f'<main class="container"><h1 class="section-title">{heading}</h1>' + product_cards(products) + '</main>'
    return page("Shop", content)


@app.route("/categories")
def categories():
    with get_db() as db:
        cats = db.execute(
            "SELECT category, image_url FROM products GROUP BY category ORDER BY MIN(id)"
        ).fetchall()
    if not cats:
        content = '<main class="container"><h1 class="section-title">Shop by Category</h1><div class="empty">Your own product pictures will appear here after you add products.</div><p style="text-align:center"><a class="btn" href="' + url_for("add_product") + '">Add Your First Product</a></p></main>'
    else:
        blocks = "".join(
            f'<a class="category" style="display:block;color:inherit;text-decoration:none" href="{url_for("shop", category=c["category"])}">'
            f'<img src="{c["image_url"]}" alt="{c["category"]}"><h2>{c["category"]}</h2>'
            f'<p>Explore our {c["category"].lower()} collection.</p></a>'
            for c in cats
        )
        content = '<main class="container"><h1 class="section-title">Shop by Category</h1><div class="category-row">' + blocks + '</div></main>'
    return page("Categories", content)


@app.route("/add-product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        price_text = request.form.get("price", "").strip()
        image_file = request.files.get("image_file")

        if not name or not category or not description or not price_text:
            flash("Please fill in every field.")
            return redirect(url_for("add_product"))
        try:
            price = float(price_text)
            if price < 0:
                raise ValueError
        except ValueError:
            flash("Please enter a valid, non-negative price.")
            return redirect(url_for("add_product"))

        if not image_file or not image_file.filename:
            flash("Please choose a picture from your computer.")
            return redirect(url_for("add_product"))
        if not allowed_file(image_file.filename):
            flash("Image must be PNG, JPG, JPEG, WEBP, or GIF.")
            return redirect(url_for("add_product"))

        safe_name = secure_filename(image_file.filename)
        unique_name = f"{uuid.uuid4().hex}_{safe_name}"
        save_path = UPLOAD_FOLDER / unique_name
        image_file.save(save_path)
        image_url = url_for("static", filename=f"uploads/{unique_name}")

        with get_db() as db:
            db.execute(
                "INSERT INTO products (name, category, price, description, image_url) VALUES (?, ?, ?, ?, ?)",
                (name, category, price, description, image_url),
            )
        flash("Product added successfully!")
        return redirect(url_for("shop"))

    content = """
    <main class="container">
      <h1 class="section-title">Add a Product</h1>
      <p style="text-align:center">Choose a photo saved on your computer. You do not need an image URL or HTML.</p>
      <form class="panel" method="post" enctype="multipart/form-data">
        <label for="name">Product name</label>
        <input id="name" name="name" required placeholder="e.g. Pink Summer Dress">

        <label for="category">Category</label>
        <select id="category" name="category" required>
          <option value="">Choose a category</option>
          <option>Dresses</option>
          <option>Tops &amp; Shirts</option>
          <option>Casual Wear</option>
        </select>

        <label for="price">Price (Rs.)</label>
        <input id="price" name="price" type="number" min="0" step="1" required placeholder="e.g. 2500">

        <label for="description">Description</label>
        <textarea id="description" name="description" required placeholder="Describe the item"></textarea>

        <label for="image_file">Product picture</label>
        <input id="image_file" name="image_file" type="file" accept="image/png,image/jpeg,image/webp,image/gif" required>
        <p class="muted">Accepted: JPG, JPEG, PNG, WEBP, GIF. Maximum file size: 8 MB.</p>

        <button type="submit">Add Product</button>
      </form>
    </main>
    """
    return page("Add Product", content)


@app.route("/order/<int:product_id>", methods=["GET", "POST"])
def order_product(product_id):
    with get_db() as db:
        product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if product is None:
        return page("Not Found", '<main class="container"><h1>Product not found</h1></main>'), 404

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        quantity_text = request.form.get("quantity", "1").strip()
        try:
            quantity = int(quantity_text)
            if quantity < 1:
                raise ValueError
        except ValueError:
            flash("Quantity must be at least 1.")
            return redirect(url_for("order_product", product_id=product_id))
        if not customer_name or not phone or not address:
            flash("Please complete all order details.")
            return redirect(url_for("order_product", product_id=product_id))
        with get_db() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    address TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    total REAL NOT NULL
                )
            """)
            db.execute(
                "INSERT INTO orders (customer_name, phone, address, product_name, quantity, total) VALUES (?, ?, ?, ?, ?, ?)",
                (customer_name, phone, address, product["name"], quantity, product["price"] * quantity),
            )
        return page("Order Received", f"""
          <main class="container" style="text-align:center">
            <h1 class="section-title">Thank you, {customer_name}!</h1>
            <p>Your order request for <strong>{product['name']}</strong> has been saved on this computer.</p>
            <p>Total: <strong>Rs. {product['price'] * quantity:,.0f}</strong></p>
            <p class="muted">This demo does not send orders online or process payments.</p>
            <a class="btn" href="{url_for('shop')}">Back to Shop</a>
          </main>
        """)

    content = f"""
    <main class="container">
      <h1 class="section-title">Order {product['name']}</h1>
      <form class="panel" method="post">
        <p><strong>Price:</strong> Rs. {product['price']:,.0f}</p>
        <label for="customer_name">Your name</label><input id="customer_name" name="customer_name" required>
        <label for="phone">Phone number</label><input id="phone" name="phone" required>
        <label for="address">Delivery address</label><textarea id="address" name="address" required></textarea>
        <label for="quantity">Quantity</label><input id="quantity" name="quantity" type="number" min="1" value="1" required>
        <button type="submit">Submit Order</button>
      </form>
    </main>
    """
    return page("Order", content)


@app.route("/orders")
def orders():
    with get_db() as db:
        table = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'").fetchone()
        rows = db.execute("SELECT * FROM orders ORDER BY id DESC").fetchall() if table else []
    if not rows:
        content = '<main class="container"><h1 class="section-title">Orders</h1><div class="empty">No orders have been placed yet.</div></main>'
    else:
        body = "".join(
            f"<tr><td>{r['id']}</td><td>{r['customer_name']}</td><td>{r['phone']}</td><td>{r['product_name']}</td><td>{r['quantity']}</td><td>Rs. {r['total']:,.0f}</td><td>{r['address']}</td></tr>"
            for r in rows
        )
        content = f"""
        <main class="container"><h1 class="section-title">Orders</h1>
        <div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;background:white">
        <thead><tr><th>ID</th><th>Customer</th><th>Phone</th><th>Product</th><th>Qty</th><th>Total</th><th>Address</th></tr></thead>
        <tbody>{body}</tbody></table></div>
        <style>th,td{{padding:10px;border:1px solid #ead9e1;text-align:left;font-size:13px}}</style>
        </main>
        """
    return page("Orders", content)


@app.route("/about")
def about():
    content = """
    <main class="container" style="max-width:800px">
      <h1 class="section-title">About Z&amp;Z</h1>
      <div class="card"><div class="card-body">
        <p>Z&amp;Z is a place for thoughtful gifts, flowers, and little moments of joy.</p>
        <p>You can add your own products and pictures using the Add Product page. Product pictures are saved in the website's <code>static/uploads</code> folder on your computer.</p>
      </div></div>
    </main>
    """
    return page("About Us", content)


@app.errorhandler(413)
def too_large(_error):
    return page("Picture Too Large", '<main class="container"><h1 class="section-title">Picture too large</h1><p style="text-align:center">Please choose a picture smaller than 8 MB.</p><p style="text-align:center"><a class="btn" href="' + url_for("add_product") + '">Go Back</a></p></main>'), 413


if __name__ == "__main__":
    init_db()
    print("Z&Z is running at http://127.0.0.1:5000")
    print("Keep this window open while using the website. Press Ctrl+C to stop.")
    app.run(debug=True)
