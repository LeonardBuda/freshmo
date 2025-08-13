import os
import json
import random
import requests
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from firebase_admin import credentials, initialize_app, firestore, get_app
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# --- Configuration Classes ---
class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-for-dev'
    SESSION_COOKIE_NAME = 'freshmo_session'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    # This will hold the raw JSON string from the environment variable (Vercel)
    # or a JSON string loaded from the local file (Development)
    FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    VAT_RATE = 0.15 # 15% VAT rate

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'development'
    # Fallback for local development: if env var isn't set, try to load from local file
    if not os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON'):
        firebase_admin_sdk_path = os.path.join(os.path.dirname(__file__), 'freshmo-14493-firebase-adminsdk-fbsvc-cd258e541d.json')
        if os.path.exists(firebase_admin_sdk_path):
            with open(firebase_admin_sdk_path, 'r') as f:
                # For local development, load the JSON file and then dump it to a string.
                # This ensures FIREBASE_SERVICE_ACCOUNT_JSON is always a string,
                # consistent with how Vercel environment variables are handled.
                Config.FIREBASE_SERVICE_ACCOUNT_JSON = json.dumps(json.load(f))
        else:
            print("WARNING: 'freshmo-14493-firebase-adminsdk-fbsvc-cd258e541d.json' not found. Firebase will only be initialized if FIREBASE_SERVICE_ACCOUNT_JSON env var is set.")


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'production'
    # Ensure SECRET_KEY and FIREBASE_SERVICE_ACCOUNT_JSON are set in production environment variables

# --- Application Factory Function ---
def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')

    # Load configuration based on environment
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    # Add custom floatformat filter for Jinja2
    def floatformat(value, decimal_places=2):
        """
        Custom Jinja2 filter to format float values to a specified number of decimal places.
        Handles cases where the input is not a valid number.
        """
        try:
            return f"{float(value):.{decimal_places}f}"
        except (ValueError, TypeError):
            return value

    app.jinja_env.filters['floatformat'] = floatformat
    
    # --- Context Processor ---
    # This makes the 'current_year' variable available to all templates.
    @app.context_processor
    def inject_current_year():
        """Inject the current year into all templates for the footer."""
        return {'current_year': datetime.now().year}

    # --- Firebase Initialization (Corrected for Vercel Environment Variables) ---
    firebase_config_json_string = app.config.get('FIREBASE_SERVICE_ACCOUNT_JSON') # Get the raw JSON string
    app.db = None # Initialize app.db to None by default

    if firebase_config_json_string:
        try:
            # Parse the JSON string into a Python dictionary
            firebase_credentials_dict = json.loads(firebase_config_json_string)

            # Check if a Firebase app with this name already exists
            try:
                # Use a specific name for your Firebase app to avoid conflicts, e.g., 'freshmo_app'
                # Pass the Flask app's name, which is 'app' by default, as the name argument
                firebase_app = get_app(name=app.name)
            except ValueError:
                # If not, initialize it using the dictionary credentials
                firebase_app = initialize_app(credentials.Certificate(firebase_credentials_dict), name=app.name)
                print("Firebase Admin SDK initialized successfully for Flask app instance.")
            
            # Obtain the Firestore client using the app instance
            app.db = firestore.client(app=firebase_app)
            print("Firestore client obtained successfully.")

        except json.JSONDecodeError as e:
            print(f"ERROR: FIREBASE_SERVICE_ACCOUNT_JSON environment variable is not valid JSON. Details: {e}")
            # Firebase will not be initialized, app.db remains None
        except Exception as e:
            print(f"Unexpected error during Firebase initialization. Details: {str(e)}")
            # Firebase will not be initialized, app.db remains None
    else:
        print("WARNING: No FIREBASE_SERVICE_ACCOUNT_JSON environment variable found. Firebase will not be available.")
        # app.db is already None


    # --- Telegram Notification Setup ---
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage" if TELEGRAM_BOT_TOKEN else None

    # New: Generic Telegram message sender
    def send_general_telegram_message(message_text, parse_mode='Markdown'):
        if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_API_URL]):
            print("Telegram bot not configured. Skipping notification. 😞")
            return

        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message_text,
            'parse_mode': parse_mode
        }
        try:
            response = requests.post(TELEGRAM_API_URL, json=payload, timeout=5)
            response.raise_for_status()
            print("Telegram notification sent successfully! 🎉")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send Telegram notification: {e} 😢")

    # The next two functions will use this general sender
    
    def send_telegram_notification(order_number, cart_items, customer_details, final_total, delivery_charge, payment_method, special_note, total_excl_vat, total_vat_amount):
        """Sends a detailed Telegram notification for a new order."""
        order_details = ""
        for item in cart_items:
            item_display_name = item['name']
            if item.get('color'):
                item_display_name += f" ({item['color'].capitalize()} color)"
            order_details += (
                f"- {item_display_name} (x{item['quantity']})\n"
                f"  Price (Excl. VAT): R{item['price_excl_vat_per_unit']:.2f}\n"
                f"  VAT: R{item['vat_amount_per_unit']:.2f}\n"
                f"  Total (Incl. VAT): R{item['price_incl_vat_per_unit']:.2f}\n"
                f"  Line Total (Incl. VAT for quantity): R{item['total_incl_vat']:.2f} 🌟\n"
            )

        message = (
            f"📦 *New Order Received!* 🚀\n"
            f"----------------------------------------\n"
            f"🛒 *Order #:* `{order_number}`\n"
            f"👤 *Customer:* {customer_details.get('name', 'N/A')} 😊\n"
            f"📱 *Phone:* {customer_details.get('phone', 'N/A')} 📞\n"
            f"📍 *Delivery/Collection:* {customer_details.get('delivery_type', 'N/A')} 🚚\n"
            f"🗺️ *Address:* {customer_details.get('address', 'N/A')} 🏠\n"
            f"----------------------------------------\n"
            f"📝 *Order Details:*\n{order_details}\n"
            f"💰 *Subtotal (Excl. VAT):* R{total_excl_vat:.2f} 💸\n"
            f"📈 *Total VAT (15%):* R{total_vat_amount:.2f} 🧾\n"
            f"🚚 *Delivery Charge:* R{delivery_charge or 0:.2f} 🚛\n"
            f"💰 *Grand Total (Incl. VAT):* R{final_total:.2f} 💳\n"
            f"💳 *Payment Method:* {payment_method} 🏧\n"
            f"----------------------------------------\n"
            f"✨ *Special Note:* {special_note if special_note else 'None'} 📝\n"
            f"⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ⏰"
        )
        send_general_telegram_message(message, parse_mode='Markdown')

    app.send_telegram_notification = send_telegram_notification # Make available to app instance

    def calculate_delivery_charge(origin, destination):
        if not GOOGLE_API_KEY:
            print("Google API key not configured. Please set GOOGLE_API_KEY in .env. 😞")
            return 0.0
        if not origin:
            print("Store address not configured. Using default: 27 Parakeet Street, Villa Lisa, Boksburg, 1459 🏠")
            origin = "27 Parakeet Street, Villa Lisa, Boksburg, 1459"
        if not destination:
            print("Destination address not provided. Skipping delivery charge calculation. 🚫")
            return 0.0

        params = {
            'origins': origin,
            'destinations': destination,
            'key': GOOGLE_API_KEY,
            'mode': 'driving'
        }
        try:
            response = requests.get(GOOGLE_DISTANCE_MATRIX_URL, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            print(f"API Response: {json.dumps(data, indent=2)} 📡")  # Detailed logging
            if data['status'] == 'OK' and data['rows'][0]['elements'][0]['status'] == 'OK':
                distance_km = data['rows'][0]['elements'][0]['distance']['value'] / 1000.0
                charge = distance_km * 6.0  # R6 per km
                print(f"Delivery charge calculated: R{charge:.2f} for {distance_km:.2f} km from {origin} to {destination} 🚚")
                return round(charge, 2)
            else:
                print(f"Distance Matrix API error: {data.get('error_message', 'Unknown error')} | Status: {data['status']} | Element Status: {data['rows'][0]['elements'][0]['status']} 😢")
                return 0.0
        except requests.exceptions.RequestException as e:
            print(f"Failed to calculate delivery charge: {e} 😞")
            return 0.0

    def get_next_order_number():
        if not app.db:
            # In-memory order number simulation
            if not hasattr(app, 'last_order_number'):
                app.last_order_number = 0
            app.last_order_number += 1
            return f"{app.last_order_number:04d}"
        try:
            # Query Firestore for the highest existing order number
            orders_ref = app.db.collection('orders')
            # Fetch all documents to find the max order_number if direct max query is not supported or indexed
            all_orders = orders_ref.stream()
            max_order_number = 0
            for order_doc in all_orders:
                order_data = order_doc.to_dict()
                if 'order_number' in order_data:
                    try:
                        max_order_number = max(max_order_number, int(order_data['order_number']))
                    except ValueError:
                        # Handle cases where order_number might not be a valid integer
                        continue
            return f"{max_order_number + 1:04d}"
        except Exception as e:
            print(f"Error generating order number from Firestore: {e} 😢. Falling back to in-memory simulation.")
            # Fallback to in-memory simulation if Firestore query fails
            if not hasattr(app, 'last_order_number'):
                app.last_order_number = 0
            app.last_order_number += 1
            return f"{app.last_order_number:04d}"

    # --- Routes ---
    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.route('/faqs')
    def faqs():
        return render_template('faqs.html')

    @app.route('/gallery')
    def gallery():
        return render_template('gallery.html')

    @app.route('/rate-us', methods=['GET', 'POST'])
    def rate_us():
        if request.method == 'POST':
            if not app.db:
                flash('Database not available. Failed to submit review. Please ensure Firebase is correctly set up. 😞', 'error')
                return redirect(url_for('rate_us'))

            product = request.form.get('product')
            rating = int(request.form.get('rating'))
            review = request.form.get('review')
            name = request.form.get('name')

            review_data = {
                'product': product,
                'rating': rating,
                'review': review,
                'name': name,
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            try:
                app.db.collection('reviews').add(review_data)
                flash('Thank you for your review! Your feedback means the world to us! 🌟', 'success')

                # Send Telegram notification for review
                review_message = (
                    f"⭐ *New Review Received!* ⭐\n"
                    f"----------------------------------------\n"
                    f"📝 *Product:* {product if product else 'N/A'}\n"
                    f"🌟 *Rating:* {rating} stars\n"
                    f"💬 *Review:* {review}\n"
                    f"👤 *Reviewer:* {name if name else 'Anonymous'}\n"
                    f"⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                send_general_telegram_message(review_message, parse_mode='Markdown')

            except Exception as e:
                flash(f'Failed to submit review: {str(e)} 😢', 'error')

            return redirect(url_for('rate_us'))
        return render_template('rate_us.html')

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            if not app.db:
                flash('Database not available. Failed to send message. Please ensure Firebase is correctly set up. 😞', 'error')
                return redirect(url_for('contact'))

            name = request.form.get('name')
            email = request.form.get('email')
            message = request.form.get('message')
            subject = request.form.get('subject') # Assuming you have a subject field

            contact_request = {
                'name': name,
                'email': email,
                'message': message,
                'subject': subject, # Add subject to Firestore
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            try:
                app.db.collection('contact_requests').add(contact_request)
                flash('Your message has been sent successfully! 🚀', 'success')

                # Send Telegram notification for contact form
                contact_message = (
                    f"📞 *New Contact Request!* 📧\n"
                    f"----------------------------------------\n"
                    f"👤 *Name:* {name}\n"
                    f"📧 *Email:* {email}\n"
                    f"📝 *Subject:* {subject if subject else 'N/A'}\n"
                    f"💬 *Message:*\n{message}\n"
                    f"⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                send_general_telegram_message(contact_message, parse_mode='Markdown')

            except Exception as e:
                flash(f'Failed to send message: {str(e)} 😢', 'error')

            return redirect(url_for('contact'))
        return render_template('contact.html')

    @app.route('/products')
    def menus():
        # Filter categories based on the updated PRODUCTS list
        available_categories = sorted(list(set(product['category'] for product in PRODUCTS)))
        
        # Define descriptions for the categories
        categories_data = {
            'Mouthwash Sachets': {'description': 'Experience instant freshness with our convenient mouthwash sachets! 💧'},
            'Oral Care Accessories': {'description': 'Enhance your oral hygiene routine with our eco-friendly accessories! 🦷'},
            'Combos': {'description': 'Get the best of both worlds with our specially curated Freshmo combos! ✨'}
        }
        
        # Create the categories dictionary to pass to the template, maintaining order
        # Ensure only categories present in PRODUCTS are shown
        ordered_categories = ['Mouthwash Sachets', 'Oral Care Accessories', 'Combos']
        categories = {cat: categories_data[cat] for cat in ordered_categories if cat in available_categories}
        
        return render_template('menus.html', categories=categories)


    @app.route('/products/<string:category_name>')
    def show_menu_category(category_name):
        category_name_display = category_name.replace('_', ' ').title()
        
        # Filter products by category
        items = [p for p in PRODUCTS if p['category'] == category_name_display]

        # Custom sort order for Mouthwash Sachets
        if category_name_display == 'Mouthwash Sachets':
            order_map = {
                'sm-single': 0,
                'sm-box': 1,
                'sm-bulk': 2
            }
            items = sorted(items, key=lambda x: order_map.get(x['id'], 999))
        else:
            # Default sort for other categories
            items = sorted(items, key=lambda x: x.get('name', ''))

        # Pass toothbrush colors if applicable
        toothbrush_colors = TOOTHBRUSH_COLORS if category_name_display in ['Oral Care Accessories', 'Combos'] else []

        # Calculate prices including VAT for display
        for item in items:
            item['price_incl_vat'] = round(item['price_excl_vat'] * (1 + VAT_RATE), 2)
            item['vat_amount'] = round(item['price_incl_vat'] - item['price_excl_vat'], 2)

        return render_template('menu_category.html', category_name=category_name_display, items=items, toothbrush_colors=toothbrush_colors)


    @app.route('/add-to-cart', methods=['POST'])
    def add_to_cart():
        item_id = request.form.get('item_id')
        item_name = request.form.get('item_name')
        # item_amount now refers to price_excl_vat
        item_price_excl_vat = float(request.form.get('item_amount')) 
        quantity = int(request.form.get('quantity', 1))
        selected_color = request.form.get('color') # Get the selected color

        # Calculate VAT and total inclusive price for the item
        vat_amount_per_unit = round(item_price_excl_vat * VAT_RATE, 2)
        price_incl_vat_per_unit = round(item_price_excl_vat + vat_amount_per_unit, 2)

        if 'cart' not in session:
            session['cart'] = []

        cart_item = {
            'id': item_id,
            'name': item_name,
            'price_excl_vat_per_unit': item_price_excl_vat,
            'vat_amount_per_unit': vat_amount_per_unit,
            'price_incl_vat_per_unit': price_incl_vat_per_unit,
            'quantity': quantity,
            'total_excl_vat': round(item_price_excl_vat * quantity, 2),
            'total_vat_amount': round(vat_amount_per_unit * quantity, 2),
            'total_incl_vat': round(price_incl_vat_per_unit * quantity, 2)
        }
        
        if selected_color:
            cart_item['color'] = selected_color
            # For display in cart, append color to name
            cart_item['name'] = f"{item_name} ({selected_color.capitalize()})" 

        item_found = False
        for item in session['cart']:
            # Check for existing item with same ID AND same color if color is present
            # This ensures adding a green toothbrush doesn't increment a blue one
            if item['id'] == item_id and item.get('color') == selected_color:
                item['quantity'] += quantity
                item['total_excl_vat'] = round(item['price_excl_vat_per_unit'] * item['quantity'], 2)
                item['total_vat_amount'] = round(item['vat_amount_per_unit'] * item['quantity'], 2)
                item['total_incl_vat'] = round(item['price_incl_vat_per_unit'] * item['quantity'], 2)
                item_found = True
                break

        if not item_found:
            session['cart'].append(cart_item)

        session.modified = True
        flash(f"Added {quantity}x {cart_item['name']} to your cart! 🛍️🎉", 'success')
        return redirect(url_for('menus'))

    @app.route('/view-cart')
    def view_cart():
        cart_items = session.get('cart', [])
        
        subtotal_excl_vat = sum(item['total_excl_vat'] for item in cart_items)
        total_vat_amount = sum(item['total_vat_amount'] for item in cart_items)
        grand_total_incl_vat = sum(item['total_incl_vat'] for item in cart_items)

        return render_template('cart.html', 
                               cart_items=cart_items, 
                               subtotal_excl_vat=subtotal_excl_vat,
                               total_vat_amount=total_vat_amount,
                               grand_total_incl_vat=grand_total_incl_vat)

    @app.route('/update-cart', methods=['POST'])
    def update_cart():
        item_id = request.form.get('item_id')
        new_quantity = int(request.form.get('quantity', 1))
        # To correctly update, you might need to pass the color here as well if it's part of the item's unique key
        # For now, it updates the first item matching the ID.

        if 'cart' in session:
            for item in session['cart']:
                if item['id'] == item_id: # Consider adding 'and item.get('color') == request.form.get('color')' for color-specific updates
                    if new_quantity > 0:
                        item['quantity'] = new_quantity
                        item['total_excl_vat'] = round(item['price_excl_vat_per_unit'] * item['quantity'], 2)
                        item['total_vat_amount'] = round(item['vat_amount_per_unit'] * item['quantity'], 2)
                        item['total_incl_vat'] = round(item['price_incl_vat_per_unit'] * item['quantity'], 2)
                    else:
                        session['cart'].remove(item)
                    break
            session.modified = True
        return redirect(url_for('view_cart'))

    @app.route('/remove-from-cart', methods=['POST'])
    def remove_from_cart():
        item_id = request.form.get('item_id')
        # To correctly remove, you might need to pass the color here as well if it's part of the item's unique key
        # For now, it removes the first item matching the ID.
        if 'cart' in session:
            session['cart'] = [item for item in session['cart'] if item['id'] != item_id] # Consider adding 'or item.get('color') != request.form.get('color')' for color-specific removal
            session.modified = True
        return redirect(url_for('view_cart'))

    @app.route('/clear-cart')
    def clear_cart():
        session.pop('cart', None)
        flash('Your cart is cleared. 🛒✅', 'success')
        return redirect(url_for('menus'))

    @app.route('/checkout', methods=['GET', 'POST'])
    def checkout():
        cart_items = session.get('cart', [])
        if not cart_items:
            flash("Your cart is empty. Please add items before checking out. 😞", "error")
            return redirect(url_for('menus'))

        subtotal_excl_vat = sum(item['total_excl_vat'] for item in cart_items)
        total_vat_amount = sum(item['total_vat_amount'] for item in cart_items)
        
        delivery_charge = 0.0
        grand_total_incl_vat = subtotal_excl_vat + total_vat_amount # Initial total before delivery

        remembered_customer = session.get('remembered_customer', {})

        if request.method == 'POST':
            customer_details = {
                'name': request.form.get('name'),
                'phone': request.form.get('phone'),
                'delivery_type': request.form.get('delivery_type'),
                'address': request.form.get('address'),
            }
            payment_method = request.form.get('payment_method')
            special_note = request.form.get('special_note')

            if customer_details['delivery_type'] == 'Delivery':
                origin = "27 Parakeet Street, Villa Lisa, Boksburg, 1459"
                delivery_charge = calculate_delivery_charge(origin, customer_details['address'])
                grand_total_incl_vat = subtotal_excl_vat + total_vat_amount + delivery_charge

            order_number = get_next_order_number()
            order_data = {
                'order_number': order_number,
                'customer_details': customer_details,
                'cart_items': cart_items,
                'subtotal_excl_vat': subtotal_excl_vat,
                'total_vat_amount': total_vat_amount,
                'delivery_charge': delivery_charge,
                'grand_total_incl_vat': grand_total_incl_vat,
                'payment_method': payment_method,
                'special_note': special_note,
                'status': 'Pending',
                'timestamp': datetime.now().isoformat()
            }

            try:
                if app.db:
                    app.db.collection('orders').add(order_data)
                send_telegram_notification(order_number, cart_items, customer_details, grand_total_incl_vat, delivery_charge, payment_method, special_note, subtotal_excl_vat, total_vat_amount)
                session.pop('cart', None)
                session.modified = True

                if request.form.get('remember'):
                    session['remembered_customer'] = customer_details
                    session.modified = True
                else:
                    session.pop('remembered_customer', None)

                flash(f"Order #{order_number} placed successfully! We will contact you shortly. 🎉🚚", 'success')
                return redirect(url_for('home'))
            except Exception as e:
                flash(f"Order failed to place: {str(e)} 😢", 'error')
                return redirect(url_for('checkout'))

        # Recalculate delivery charge if remembered customer is delivery type on GET request
        if remembered_customer and remembered_customer.get('delivery_type') == 'Delivery':
            origin = "27 Parakeet Street, Villa Lisa, Boksburg, 1459"
            delivery_charge = calculate_delivery_charge(origin, remembered_customer.get('address', ''))
            grand_total_incl_vat = subtotal_excl_vat + total_vat_amount + delivery_charge

        return render_template('checkout.html', 
                               cart_items=cart_items, 
                               subtotal_excl_vat=subtotal_excl_vat,
                               total_vat_amount=total_vat_amount,
                               delivery_charge=delivery_charge, 
                               grand_total_incl_vat=grand_total_incl_vat, 
                               remembered_customer=remembered_customer)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    if not app.config.get('SECRET_KEY'):
        app.secret_key = 'your-very-secret-key-replace-this'
    app.run(debug=True)
