from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, current_app
import uuid # For generating unique order IDs
from firebase_admin import firestore # Import firestore client

shop_bp = Blueprint('shop', __name__)

# No more DUMMY_MENU here, we will fetch from Firestore

def get_firestore_products():
    """Fetches all products from Firestore, grouped by category."""
    db = current_app.db # Access Firestore client from app context
    products_ref = db.collection('products')
    
    # Order by category and then by name for consistent display
    docs = products_ref.order_by('category').order_by('name').stream()
    
    menu_data = {}
    for doc in docs:
        product = doc.to_dict()
        product['id'] = doc.id # Ensure the document ID is included
        category = product.get('category', 'Uncategorized')
        
        if category not in menu_data:
            # For each category, get its description. You might store this in a separate 'categories' collection
            # For now, we'll use a simple default or derive from product data.
            # A more robust solution would be to have a 'categories' collection in Firestore.
            description = ""
            if category == "Mouthwash Sachets":
                description = "Freshmo's signature on-the-go mouthwash sachets."
            elif category == "Oral Care Accessories":
                description = "Eco-friendly accessories for a complete oral care routine."
            elif category == "Guest Amenities":
                description = "Convenient oral care and beverage solutions for hospitality."
            elif category == "Coming Soon": # For future products
                description = "Exciting new products on the horizon!"
            else:
                description = f"Explore our {category} selection!"

            menu_data[category] = {"description": description, "items": []}
            
        menu_data[category]["items"].append(product)
        
    return menu_data

@shop_bp.route('/menus')
def menus():
    """Renders the main menus page, showing categories fetched from Firestore."""
    try:
        menu_data = get_firestore_products()
        menu_categories = menu_data.keys()
        return render_template('menus.html', menu=menu_data, menu_categories=menu_categories)
    except Exception as e:
        flash(f"Error loading products: {str(e)}", "error")
        return render_template('menus.html', menu={}, menu_categories=[])


@shop_bp.route('/menu_category/<category_name>')
def show_menu_category(category_name):
    """Renders a specific menu category page with items fetched from Firestore."""
    display_category_name = category_name.replace('_', ' ').title()
    
    try:
        menu_data = get_firestore_products()
        if display_category_name in menu_data:
            category_data = menu_data[display_category_name]
            return render_template('menu_category.html',
                                   category_name=display_category_name,
                                   category_data=category_data)
        else:
            flash("Category not found.", "error")
            return redirect(url_for('shop.menus'))
    except Exception as e:
        flash(f"Error loading category: {str(e)}", "error")
        return redirect(url_for('shop.menus'))


@shop_bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Adds an item to the shopping cart."""
    item_id = request.form.get('item_id')
    item_name = request.form.get('item_name')
    item_amount = float(request.form.get('item_amount'))
    quantity = int(request.form.get('quantity', 1)) # Default to 1 if not specified

    if 'cart' not in session:
        session['cart'] = []

    # Check if item already exists in cart, update quantity
    found = False
    for item in session['cart']:
        if item['id'] == item_id:
            item['quantity'] += quantity
            item['total'] = item['quantity'] * item['amount']
            found = True
            break
    if not found:
        session['cart'].append({
            'id': item_id,
            'name': item_name,
            'amount': item_amount,
            'quantity': quantity,
            'total': quantity * item_amount
        })

    session.modified = True # Important to tell Flask that session has been modified
    flash(f'{quantity} x {item_name} added to cart! 🛒', 'success')
    return redirect(request.referrer or url_for('shop.menus'))

@shop_bp.route('/remove_from_cart/<item_id>')
def remove_from_cart(item_id):
    """Removes an item from the shopping cart."""
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['id'] != item_id]
        session.modified = True
        flash('Item removed from cart. 🗑️', 'success')
    return redirect(url_for('shop.view_cart'))

@shop_bp.route('/update_cart_quantity', methods=['POST'])
def update_cart_quantity():
    """Updates the quantity of an item in the cart."""
    item_id = request.form.get('item_id')
    new_quantity = int(request.form.get('quantity'))

    if 'cart' in session:
        for item in session['cart']:
            if item['id'] == item_id:
                if new_quantity > 0:
                    item['quantity'] = new_quantity
                    item['total'] = item['quantity'] * item['amount']
                    flash(f'Quantity for {item["name"]} updated to {new_quantity}.', 'info')
                else:
                    session['cart'].remove(item)
                    flash(f'{item["name"]} removed from cart.', 'info')
                break
        session.modified = True
    return redirect(url_for('shop.view_cart'))


@shop_bp.route('/cart')
def view_cart():
    """Renders the shopping cart page."""
    cart_items = session.get('cart', [])
    total_amount = sum(item['total'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)

@shop_bp.route('/clear_cart')
def clear_cart():
    """Clears all items from the shopping cart."""
    session.pop('cart', None)
    session.modified = True
    flash('Your cart has been cleared. 🗑️', 'info')
    return redirect(url_for('shop.menus'))

@shop_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Handles the checkout process."""
    cart_items = session.get('cart', [])
    if not cart_items:
        flash('Your cart is empty. Please add items before checking out. 😞', 'error')
        return redirect(url_for('shop.menus'))

    total_amount = sum(item['total'] for item in cart_items)

    # Retrieve remembered customer details if available
    remembered_customer = session.get('remembered_customer', {})

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        delivery_option = request.form.get('delivery_option') # 'delivery' or 'collection'
        address = request.form.get('address') if delivery_option == 'delivery' else 'N/A'
        special_note = request.form.get('special_note')
        payment_method = request.form.get('payment_method')
        remember_details = request.form.get('remember') == 'on'

        # Basic validation
        if not all([first_name, last_name, phone, email, delivery_option, payment_method]):
            flash('Please fill in all required customer details.', 'error')
            return render_template('checkout.html', cart_items=cart_items, total_amount=total_amount, remembered_customer=remembered_customer)

        if delivery_option == 'delivery' and not address:
            flash('Please provide a delivery address.', 'error')
            return render_template('checkout.html', cart_items=cart_items, total_amount=total_amount, remembered_customer=remembered_customer)

        customer_details = {
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'email': email,
            'delivery_option': delivery_option,
            'address': address,
            'special_note': special_note
        }

        # Remember customer details if checkbox is ticked
        if remember_details:
            session['remembered_customer'] = customer_details
        else:
            session.pop('remembered_customer', None)

        try:
            # Generate a unique order number
            order_number = str(uuid.uuid4()).split('-')[0].upper() # Short UUID for display

            # Prepare order data for Firestore
            order_data = {
                'order_number': order_number,
                'order_date': datetime.now(),
                'total_amount_zar': total_amount,
                'status': 'pending', # Initial status
                'customer_details': customer_details,
                'items': cart_items,
                'payment_method': payment_method,
                'payment_status': 'pending' # Payment status will be updated after actual payment integration
            }

            # Save order to Firestore
            db = current_app.db # Access Firestore client from app context
            orders_ref = db.collection('orders')
            orders_ref.add(order_data)

            # Send Telegram notification
            current_app.send_telegram_notification(order_number, cart_items, customer_details, total_amount, payment_method, special_note=None)

            # Clear cart after successful order
            session.pop('cart', None)
            session.modified = True

            flash(f'Your order ({order_number}) has been placed successfully! 🎉 We will contact you shortly. 🚀', 'success')
            return redirect(url_for('shop.order_confirmation', order_id=order_number)) # Redirect to a confirmation page

        except Exception as e:
            flash(f'An error occurred while placing your order: {str(e)} 😞 Please try again.', 'error')
            # Render the checkout page again with current form data
            return render_template('checkout.html', cart_items=cart_items, total_amount=total_amount,
                                   form_data=request.form, remembered_customer=remembered_customer)

    return render_template('checkout.html', cart_items=cart_items, total_amount=total_amount, remembered_customer=remembered_customer)

@shop_bp.route('/order_confirmation/<order_id>')
def order_confirmation(order_id):
    """Renders the order confirmation page."""
    # In a real app, you might fetch order details from Firestore to display
    return render_template('order_confirmation.html', order_id=order_id)