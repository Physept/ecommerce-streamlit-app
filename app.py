# E-Commerce Database Project
# Main application file: app.py (SQLite Version)

import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import hashlib
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import os

# Database configuration
DATABASE_PATH = 'ecommerce.db'

# Database connection
def create_connection():
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row  # This makes rows behave like dictionaries
        return connection
    except Exception as e:
        st.error(f"Error connecting to SQLite: {e}")
        return None

# Initialize database and tables
def init_database():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    
    # Create tables
    tables = {
        'categories': """
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        
        'products': """
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                category_id INTEGER,
                price DECIMAL(10, 2) NOT NULL,
                stock_quantity INTEGER DEFAULT 0,
                description TEXT,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(category_id)
            )
        """,
        
        'customers': """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                country TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        
        'orders': """
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_amount DECIMAL(10, 2) NOT NULL,
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')),
                shipping_address TEXT,
                payment_method TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
        """,
        
        'order_items': """
            CREATE TABLE IF NOT EXISTS order_items (
                order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL,
                subtotal DECIMAL(10, 2) NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(order_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            )
        """,
        
        'cart': """
            CREATE TABLE IF NOT EXISTS cart (
                cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            )
        """,
        
        'reviews': """
            CREATE TABLE IF NOT EXISTS reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                customer_id INTEGER,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(product_id),
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
        """
    }
    
    for table_name, create_query in tables.items():
        cursor.execute(create_query)
    
    connection.commit()
    cursor.close()
    connection.close()

# Hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Authentication
def authenticate_user(email, password):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        query = "SELECT * FROM customers WHERE email = ? AND password_hash = ?"
        cursor.execute(query, (email, hash_password(password)))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            return dict(user)  # Convert Row to dict
        return None
    return None

# Register new customer
def register_customer(data):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        query = """
            INSERT INTO customers (first_name, last_name, email, password_hash, phone, address, city, state, zip_code, country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            data['first_name'], data['last_name'], data['email'],
            hash_password(data['password']), data['phone'],
            data['address'], data['city'], data['state'],
            data['zip_code'], data['country']
        )
        try:
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Registration failed: {e}")
            cursor.close()
            conn.close()
            return False
    return False

# Product Management Functions - FIXED VERSION
def add_product(data):
    """
    Add a new product to the database.
    data should be a dictionary containing product information.
    """
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        query = """
            INSERT INTO products (product_name, category_id, price, stock_quantity, description, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        values = (
            data['name'],
            data['category_id'],
            data['price'],
            data['stock'],
            data['description'],
            data.get('image_url', '')  # Use empty string if image_url not provided
        )
        
        try:
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Failed to add product: {e}")
            cursor.close()
            conn.close()
            return False
    return False
    
def get_products():
    conn = create_connection()
    if conn:
        query = """
            SELECT p.*, c.category_name 
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.category_id
            ORDER BY p.created_at DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

def get_categories():
    conn = create_connection()
    if conn:
        query = "SELECT * FROM categories ORDER BY category_name"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

def add_category(name, description):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        query = "INSERT INTO categories (category_name, description) VALUES (?, ?)"
        try:
            cursor.execute(query, (name, description))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Failed to add category: {e}")
            cursor.close()
            conn.close()
            return False
    return False

# Cart Functions
def add_to_cart(customer_id, product_id, quantity):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        # Check if item already in cart
        check_query = "SELECT * FROM cart WHERE customer_id = ? AND product_id = ?"
        cursor.execute(check_query, (customer_id, product_id))
        existing = cursor.fetchone()
        
        if existing:
            # Update quantity
            update_query = "UPDATE cart SET quantity = quantity + ? WHERE customer_id = ? AND product_id = ?"
            cursor.execute(update_query, (quantity, customer_id, product_id))
        else:
            # Insert new item
            insert_query = "INSERT INTO cart (customer_id, product_id, quantity) VALUES (?, ?, ?)"
            cursor.execute(insert_query, (customer_id, product_id, quantity))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    return False

def get_cart_items(customer_id):
    conn = create_connection()
    if conn:
        query = """
            SELECT c.*, p.product_name, p.price, p.image_url, (c.quantity * p.price) as subtotal
            FROM cart c
            JOIN products p ON c.product_id = p.product_id
            WHERE c.customer_id = ?
        """
        df = pd.read_sql(query, conn, params=[customer_id])
        conn.close()
        return df
    return pd.DataFrame()

def clear_cart(customer_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE customer_id = ?", (customer_id,))
        conn.commit()
        cursor.close()
        conn.close()

# Order Functions
def create_order(customer_id, cart_items, shipping_address, payment_method):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        
        # Calculate total
        total = cart_items['subtotal'].sum()
        
        # Create order
        order_query = """
            INSERT INTO orders (customer_id, total_amount, shipping_address, payment_method)
            VALUES (?, ?, ?, ?)
        """
        cursor.execute(order_query, (customer_id, total, shipping_address, payment_method))
        order_id = cursor.lastrowid
        
        # Add order items
        for _, item in cart_items.iterrows():
            item_query = """
                INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
                VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(item_query, (order_id, item['product_id'], item['quantity'], 
                                       item['price'], item['subtotal']))
            
            # Update product stock
            stock_query = "UPDATE products SET stock_quantity = stock_quantity - ? WHERE product_id = ?"
            cursor.execute(stock_query, (item['quantity'], item['product_id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        return order_id
    return None

def get_orders(customer_id=None):
    conn = create_connection()
    if conn:
        if customer_id:
            query = """
                SELECT o.*, c.first_name, c.last_name, c.email
                FROM orders o
                JOIN customers c ON o.customer_id = c.customer_id
                WHERE o.customer_id = ?
                ORDER BY o.order_date DESC
            """
            df = pd.read_sql(query, conn, params=[customer_id])
        else:
            query = """
                SELECT o.*, c.first_name, c.last_name, c.email
                FROM orders o
                JOIN customers c ON o.customer_id = c.customer_id
                ORDER BY o.order_date DESC
            """
            df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

# Analytics Functions
def get_sales_analytics():
    conn = create_connection()
    if conn:
        # Daily sales
        daily_sales_query = """
            SELECT DATE(order_date) as date, COUNT(*) as orders, SUM(total_amount) as revenue
            FROM orders
            WHERE order_date >= DATE('now', '-30 days')
            GROUP BY DATE(order_date)
            ORDER BY date
        """
        daily_sales = pd.read_sql(daily_sales_query, conn)
        
        # Top products
        top_products_query = """
            SELECT p.product_name, SUM(oi.quantity) as total_sold, SUM(oi.subtotal) as revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            GROUP BY p.product_id
            ORDER BY total_sold DESC
            LIMIT 10
        """
        top_products = pd.read_sql(top_products_query, conn)
        
        # Category sales
        category_sales_query = """
            SELECT c.category_name, COUNT(DISTINCT oi.order_id) as orders, SUM(oi.subtotal) as revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            JOIN categories c ON p.category_id = c.category_id
            GROUP BY c.category_id
            ORDER BY revenue DESC
        """
        category_sales = pd.read_sql(category_sales_query, conn)
        
        conn.close()
        return daily_sales, top_products, category_sales
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Add this function to your app.py file

def view_database_tables():
    """Function to view all database tables and their data"""
    conn = create_connection()
    if not conn:
        st.error("Cannot connect to database")
        return
    
    try:
        # Get all table names
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        cursor.close()
        
        # Display each table
        for table_name in tables:
            with st.expander(f"📋 Table: {table_name.upper()}", expanded=False):
                try:
                    # Get table data
                    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                    
                    if not df.empty:
                        # Show basic info
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Rows", len(df))
                        with col2:
                            st.metric("Columns", len(df.columns))
                        with col3:
                            # Get table size
                            cursor = conn.cursor()
                            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                            count = cursor.fetchone()[0]
                            cursor.close()
                            st.metric("Records", count)
                        
                        # Show table structure
                        if st.checkbox(f"Show table structure for {table_name}", key=f"structure_{table_name}"):
                            cursor = conn.cursor()
                            cursor.execute(f"PRAGMA table_info({table_name})")
                            structure = cursor.fetchall()
                            cursor.close()
                            
                            structure_df = pd.DataFrame(structure, 
                                columns=['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk'])
                            st.dataframe(structure_df, use_container_width=True)
                        
                        # Show data
                        if st.checkbox(f"Show data for {table_name}", key=f"data_{table_name}"):
                            # Pagination for large tables
                            if len(df) > 100:
                                st.warning(f"Large table ({len(df)} rows). Showing first 100 rows.")
                                st.dataframe(df.head(100), use_container_width=True)
                            else:
                                st.dataframe(df, use_container_width=True)
                        
                        # Quick stats for numeric columns
                        numeric_cols = df.select_dtypes(include=[np.number]).columns
                        if len(numeric_cols) > 0 and st.checkbox(f"Show statistics for {table_name}", key=f"stats_{table_name}"):
                            st.write("**Numeric Column Statistics:**")
                            st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                    
                    else:
                        st.info(f"Table '{table_name}' is empty")
                        
                        # Still show structure for empty tables
                        cursor = conn.cursor()
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        structure = cursor.fetchall()
                        cursor.close()
                        
                        structure_df = pd.DataFrame(structure, 
                            columns=['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk'])
                        st.write("**Table Structure:**")
                        st.dataframe(structure_df, use_container_width=True)
                
                except Exception as e:
                    st.error(f"Error reading table {table_name}: {e}")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error accessing database: {e}")
        if conn:
            conn.close()

# Streamlit App
def main():
    st.set_page_config(page_title="E-Commerce Database System", layout="wide")
    
    # Initialize database
    if 'db_initialized' not in st.session_state:
        init_database()
        st.session_state.db_initialized = True
    
    # Session management
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    # Sidebar
    with st.sidebar:
        st.title("🛍️ E-Commerce System")
        
        if st.session_state.user:
            st.success(f"Welcome, {st.session_state.user['first_name']}!")
            if st.button("Logout"):
                st.session_state.user = None
                st.rerun()
        else:
            auth_mode = st.radio("Choose", ["Login", "Register"])
            
            if auth_mode == "Login":
                with st.form("login_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    if st.form_submit_button("Login"):
                        user = authenticate_user(email, password)
                        if user:
                            st.session_state.user = user
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid credentials")
            
            else:
                with st.form("register_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        first_name = st.text_input("First Name")
                        last_name = st.text_input("Last Name")
                        email = st.text_input("Email")
                        password = st.text_input("Password", type="password")
                        phone = st.text_input("Phone")
                    with col2:
                        address = st.text_area("Address")
                        city = st.text_input("City")
                        state = st.text_input("State")
                        zip_code = st.text_input("ZIP Code")
                        country = st.text_input("Country")
                    
                    if st.form_submit_button("Register"):
                        data = {
                            'first_name': first_name, 'last_name': last_name,
                            'email': email, 'password': password, 'phone': phone,
                            'address': address, 'city': city, 'state': state,
                            'zip_code': zip_code, 'country': country
                        }
                        if register_customer(data):
                            st.success("Registration successful! Please login.")
                        else:
                            st.error("Registration failed")
    
    # Main content
    if st.session_state.user:
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🛒 Shop", "🛍️ Cart", "📦 Orders", "⚙️ Admin", "📊 Analytics", "🗄️ Database"])
        
        with tab1:
            st.header("Products")
            
            # Search and filter
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                search = st.text_input("Search products", "")
            with col2:
                categories = get_categories()
                if not categories.empty:
                    category_filter = st.selectbox("Category", ["All"] + categories['category_name'].tolist())
                else:
                    category_filter = "All"
            with col3:
                sort_by = st.selectbox("Sort by", ["Name", "Price: Low to High", "Price: High to Low"])
            
            # Get products
            products = get_products()
            
            # Apply filters
            if search:
                products = products[products['product_name'].str.contains(search, case=False)]
            if category_filter != "All":
                products = products[products['category_name'] == category_filter]
            
            # Apply sorting
            if sort_by == "Name":
                products = products.sort_values('product_name')
            elif sort_by == "Price: Low to High":
                products = products.sort_values('price')
            else:
                products = products.sort_values('price', ascending=False)
            
            # Display products
            if not products.empty:
                cols = st.columns(3)
                for idx, product in products.iterrows():
                    with cols[idx % 3]:
                        st.subheader(product['product_name'])
                        if product['image_url']:
                            st.image(product['image_url'], use_container_width=True)
                        st.write(f"**Price:** ${product['price']:.2f}")
                        st.write(f"**Category:** {product['category_name']}")
                        st.write(f"**Stock:** {product['stock_quantity']} units")
                        st.write(product['description'][:100] + "..." if len(str(product['description'])) > 100 else product['description'])
                        
                        quantity = st.number_input(f"Qty", min_value=1, max_value=product['stock_quantity'], 
                                                  value=1, key=f"qty_{product['product_id']}")
                        if st.button(f"Add to Cart", key=f"add_{product['product_id']}"):
                            if add_to_cart(st.session_state.user['customer_id'], product['product_id'], quantity):
                                st.success(f"Added {quantity} x {product['product_name']} to cart!")
            else:
                st.info("No products available")
        
        with tab2:
            st.header("Shopping Cart")
            
            cart_items = get_cart_items(st.session_state.user['customer_id'])
            
            if not cart_items.empty:
                # Display cart items
                for _, item in cart_items.iterrows():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    with col1:
                        st.write(f"**{item['product_name']}**")
                    with col2:
                        st.write(f"${item['price']:.2f}")
                    with col3:
                        st.write(f"Qty: {item['quantity']}")
                    with col4:
                        st.write(f"${item['subtotal']:.2f}")
                
                st.divider()
                st.subheader(f"Total: ${cart_items['subtotal'].sum():.2f}")
                
                # Checkout form
                with st.form("checkout_form"):
                    shipping_address = st.text_area("Shipping Address")
                    payment_method = st.selectbox("Payment Method", ["Credit Card", "Debit Card", "PayPal", "Cash on Delivery"])
                    
                    if st.form_submit_button("Place Order"):
                        order_id = create_order(st.session_state.user['customer_id'], cart_items, 
                                              shipping_address, payment_method)
                        if order_id:
                            clear_cart(st.session_state.user['customer_id'])
                            st.success(f"Order #{order_id} placed successfully!")
                            st.rerun()
            else:
                st.info("Your cart is empty")
        
        with tab3:
            st.header("Your Orders")
            
            orders = get_orders(st.session_state.user['customer_id'])
            
            if not orders.empty:
                for _, order in orders.iterrows():
                    with st.expander(f"Order #{order['order_id']} - {order['order_date']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Total:** ${order['total_amount']:.2f}")
                            st.write(f"**Status:** {order['status']}")
                        with col2:
                            st.write(f"**Payment:** {order['payment_method']}")
                            st.write(f"**Shipping:** {order['shipping_address']}")
            else:
                st.info("No orders yet")
        
        with tab4:
            st.header("Admin Panel")
            
            admin_tab1, admin_tab2 = st.tabs(["Manage Products", "Manage Categories"])
            
            with admin_tab1:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.subheader("Add Product")
                    with st.form("add_product_form"):
                        name = st.text_input("Product Name")
                        categories = get_categories()
                        if not categories.empty:
                            category = st.selectbox("Category", categories['category_name'].tolist())
                            category_id = categories[categories['category_name'] == category]['category_id'].values[0]
                        else:
                            category_id = None
                            st.warning("No categories available. Please add categories first.")
                        price = st.number_input("Price", min_value=0.0, step=0.01)
                        stock = st.number_input("Stock Quantity", min_value=0, step=1)
                        description = st.text_area("Description")
                        image_url = st.text_input("Image URL (optional)")
                        
                        if st.form_submit_button("Add Product"):
                            if not name.strip():
                                st.error("Product name is required!")
                            elif category_id is None:
                                st.error("Please add categories first!")
                            elif price <= 0:
                                st.error("Price must be greater than 0!")
                            else:
                                product_data = {
                                    'name': name.strip(),
                                    'category_id': int(category_id),
                                    'price': float(price),
                                    'stock': int(stock),
                                    'description': description.strip(),
                                    'image_url': image_url.strip()
                                }
                                
                                if add_product(product_data):
                                    st.success(f"Product '{name}' added successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to add product!")
                
                with col2:
                    st.subheader("Current Products")
                    products = get_products()
                    if not products.empty:
                        # Show more details and add refresh button
                        if st.button("🔄 Refresh Products", key="refresh_products"):
                            st.rerun()
                        
                        # Display products in a more user-friendly format
                        for idx, product in products.iterrows():
                            with st.expander(f"{product['product_name']} - ${product['price']:.2f}"):
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    st.write(f"**Category:** {product['category_name']}")
                                    st.write(f"**Stock:** {product['stock_quantity']} units")
                                    st.write(f"**Created:** {product['created_at']}")
                                with col_b:
                                    st.write(f"**Product ID:** {product['product_id']}")
                                    if product['image_url']:
                                        st.write(f"**Image:** [Link]({product['image_url']})")
                                    st.write(f"**Updated:** {product['updated_at']}")
                                if product['description']:
                                    st.write(f"**Description:** {product['description']}")
                    else:
                        st.info("No products found. Add some products to get started!")
            
            with admin_tab2:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.subheader("Add Category")
                    with st.form("add_category_form"):
                        cat_name = st.text_input("Category Name")
                        cat_desc = st.text_area("Description")
                        
                        if st.form_submit_button("Add Category"):
                            if not cat_name.strip():
                                st.error("Category name is required!")
                            else:
                                if add_category(cat_name.strip(), cat_desc.strip()):
                                    st.success(f"Category '{cat_name}' added successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to add category!")
                
                with col2:
                    st.subheader("Current Categories")
                    categories = get_categories()
                    if not categories.empty:
                        if st.button("🔄 Refresh Categories", key="refresh_categories"):
                            st.rerun()
                        st.dataframe(categories[['category_name', 'description']], use_container_width=True)
                    else:
                        st.info("No categories found. Add some categories to get started!")
        
        with tab5:
            st.header("Analytics Dashboard")
            
            daily_sales, top_products, category_sales = get_sales_analytics()
            
            col1, col2 = st.columns(2)
            
            with col1:
                if not daily_sales.empty:
                    fig = px.line(daily_sales, x='date', y='revenue', title='Daily Revenue (Last 30 Days)')
                    st.plotly_chart(fig, use_container_width=True)
                
                if not category_sales.empty:
                    fig = px.pie(category_sales, values='revenue', names='category_name', title='Revenue by Category')
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if not daily_sales.empty:
                    fig = px.bar(daily_sales, x='date', y='orders', title='Daily Orders (Last 30 Days)')
                    st.plotly_chart(fig, use_container_width=True)
                
                if not top_products.empty:
                    fig = px.bar(top_products.head(5), x='product_name', y='total_sold', title='Top 5 Products by Sales')
                    st.plotly_chart(fig, use_container_width=True)
            
            # Summary metrics
            if not daily_sales.empty:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Revenue", f"${daily_sales['revenue'].sum():,.2f}")
                with col2:
                    st.metric("Total Orders", f"{daily_sales['orders'].sum():,}")
                with col3:
                    st.metric("Avg Order Value", f"${daily_sales['revenue'].sum() / daily_sales['orders'].sum():.2f}")
                with col4:
                    st.metric("Daily Avg Revenue", f"${daily_sales['revenue'].mean():,.2f}")
        with tab6:
            st.header("🗄️ Database Viewer")
            st.write("View all database tables and their contents")
            
            # Refresh button
            if st.button("🔄 Refresh Database View"):
                st.rerun()
            
            # Add custom query section
            with st.expander("🔍 Custom SQL Query", expanded=False):
                st.warning("⚠️ Be careful with custom queries. Only use SELECT statements.")
                custom_query = st.text_area("Enter SQL Query:", 
                    placeholder="SELECT * FROM products WHERE price > 100;")
                
                if st.button("Execute Query"):
                    if custom_query.strip().upper().startswith('SELECT'):
                        try:
                            conn = create_connection()
                            if conn:
                                result_df = pd.read_sql(custom_query, conn)
                                conn.close()
                                st.success("Query executed successfully!")
                                st.dataframe(result_df, use_container_width=True)
                        except Exception as e:
                            st.error(f"Query error: {e}")
                    else:
                        st.error("Only SELECT queries are allowed for safety!")
            
            # Show all tables
            st.subheader("All Database Tables")
            view_database_tables()
    
    else:
        st.header("Welcome to E-Commerce Database System")
        st.info("Please login or register to continue")
        
        # Show some stats
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products")
            product_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM categories")
            category_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Available Products", product_count)
            with col2:
                st.metric("Categories", category_count)

if __name__ == "__main__":
    main()