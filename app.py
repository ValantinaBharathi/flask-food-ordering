from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo
from flask_session import Session

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config["MONGO_URI"] = "mongodb://localhost:27017/mlops"
mongo = PyMongo(app)

menu_collection = mongo.db.menu
orders_collection = mongo.db.orders

# Updated menu data with stock information
menu_data = [
    {
        "name": "Hot Pot", 
        "description": "Fresh meats and veggies cooked in a flavorful broth at your table.", 
        "price": 550, 
        "image": "hot pot.jpg",
        "stock": 10  # Initial stock count
    },
    {
        "name": "Kung Pao Chicken", 
        "description": "Spicy chicken stir-fried with peanuts and crisp veggies.", 
        "price": 700, 
        "image": "Kung pao chicken.jpg",
        "stock": 5  # Initial stock count
    },
    {
        "name": "Steamed Pork Buns", 
        "description": "Fluffy buns filled with savory, seasoned pork.", 
        "price": 400, 
        "image": "steamed pork buns.jpg",
        "stock": 8  # Initial stock count
    },
    {
        "name": "Stinky Tofu", 
        "description": "Flavorful and versatile protein, prepared to your liking", 
        "price": 350, 
        "image": "tofu.jpg",
        "stock": 0  # Out of stock initially
    },
    {
        "name": "Chinese Sticky Rice", 
        "description": "Chewy glutinous rice, perfect for pairing with any dish.", 
        "price": 250, 
        "image": "sticky rice.jpg",
        "stock": 15  # Initial stock count
    }
]

# Check if the menu is already populated
if menu_collection.count_documents({}) == 0:
    menu_collection.insert_many(menu_data)

@app.route('/')
def menu():
    # Retrieve all items from the menu collection
    items = list(menu_collection.find())
    return render_template('menu.html', items=items)

@app.route('/add_to_cart/<name>', methods=['POST'])
def add_to_cart(name):
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    
    item = menu_collection.find_one({"name": name})
    
    if item and item['stock'] >= quantity:
        cart[name] = cart.get(name, 0) + quantity
        # Update stock in the database
        menu_collection.update_one({"name": name}, {"$inc": {"stock": -quantity}})
        
    else:
        flash(f"Sorry, {name} is out of stock or insufficient quantity available.", 'error')
    
    session['cart'] = cart
    return redirect(url_for('menu'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    items = {item['name']: item for item in menu_collection.find()}
    cart_items = [(name, items[name], quantity) for name, quantity in cart.items() if name in items]
    
    subtotal = sum(item['price'] * qty for _, item, qty in cart_items)
    delivery_fee = 5 if subtotal > 0 else 0
    total = subtotal + delivery_fee

    return render_template('cart.html', cart_items=cart_items, subtotal=subtotal,
                           delivery_fee=delivery_fee, total=total)

@app.route('/update_cart/<name>', methods=['POST'])
def update_cart(name):
    new_quantity = int(request.form.get('quantity'))
    cart = session.get('cart', {})

    if new_quantity <= 0:
        # Restore stock when an item is removed from the cart
        item = menu_collection.find_one({"name": name})
        if item:
            menu_collection.update_one({"name": name}, {"$inc": {"stock": cart[name]}})
        
        cart.pop(name, None)  # Remove item if quantity is 0
    else:
        # Check if there's enough stock before updating
        item = menu_collection.find_one({"name": name})
        
        if item and item['stock'] + cart[name] >= new_quantity:
            # Update stock accordingly
            menu_collection.update_one({"name": name}, {"$inc": {"stock": cart[name] - new_quantity}})
            cart[name] = new_quantity
        else:
            flash(f"Cannot update {name}. Not enough stock available.", 'error')
    
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    cart = session.pop('cart', {})
    if cart:
        orders_collection.insert_one({"order": cart})
    
    return render_template('checkout.html')

if __name__ == '__main__':
    app.run(debug=True)
