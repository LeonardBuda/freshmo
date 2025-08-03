import os
import json
import random
import requests
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from firebase_admin import credentials, initialize_app, firestore, get_app
from dotenv import load_dotenv
from flask_moment import Moment

load_dotenv()

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    moment = Moment(app)

    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        app.config.from_object('config.ProductionConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')

    def floatformat(value, decimal_places=2):
        try:
            return f"{float(value):.{decimal_places}f}"
        except (ValueError, TypeError):
            return value

    app.jinja_env.filters['floatformat'] = floatformat

    # Initialize Firestore only for contact and rate_us (optional)
    firebase_credentials = app.config.get('FIREBASE_CONFIG')
    if firebase_credentials:
        try:
            try:
                get_app()
            except ValueError:
                cred = credentials.Certificate(firebase_credentials)
                initialize_app(cred)
                print("Firebase Admin SDK initialized successfully.")
            db = firestore.client()
            app.db = db
            print("Firestore client obtained and attached to app.")
        except ValueError as e:
            print(f"Firebase app already initialized: {e}")
            db = firestore.client()
            app.db = db
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            app.db = None
    else:
        print("WARNING: Firebase credentials not found. Contact and review features may be limited.")
        app.db = None

    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8469942529:AAGi4UIWOAX5zRymx6OvkQa8jSgQtwCf4oo')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-4987724024')
    TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage" if TELEGRAM_BOT_TOKEN else None

    GOOGLE_API_KEY = app.config.get('GOOGLE_API_KEY')
    GOOGLE_DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

    # Static product list
    PRODUCTS = [
        {'id': '1', 'name': 'Mint Single Sachet', 'category': 'Mouthwash Sachets', 'price_zar': 6.99, 'type': 'single'},
        {'id': '2', 'name': 'Mint Box', 'category': 'Mouthwash Sachets', 'price_zar': 160.00, 'type': 'box'},
        {'id': '3', 'name': 'Strawberry Mint Single Sachet', 'category': 'Mouthwash Sachets', 'price_zar': 6.99, 'type': 'single'},
        {'id': '4', 'name': 'Strawberry Mint Box', 'category': 'Mouthwash Sachets', 'price_zar': 160.00, 'type': 'box'},
        {'id': '5', 'name': 'Apple Single Sachet', 'category': 'Mouthwash Sachets', 'price_zar': 6.99, 'type': 'single'},
        {'id': '6', 'name': 'Apple Box', 'category': 'Mouthwash Sachets', 'price_zar': 160.00, 'type': 'box'},
        {'id': '7', 'name': 'Watermelon Single Sachet', 'category': 'Mouthwash Sachets', 'price_zar': 6.99, 'type': 'single'},
        {'id': '8', 'name': 'Watermelon Box', 'category': 'Mouthwash Sachets', 'price_zar': 160.00, 'type': 'box'},
        {'id': '9', 'name': 'Toothbrush Set', 'category': 'Oral Care Accessories', 'price_zar': 50.00},
        {'id': '10', 'name': 'Shampoo Sachet', 'category': 'Guest Amenities', 'price_zar': 10.00}
    ]

    def send_telegram_notification(order_number, cart_items, customer_details, final_total, delivery_charge, payment_method, special_note):
        if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_API_URL]):
            print("Telegram bot not configured. Skipping notification. 😞")
            return

        order_details = ""
        for item in cart_items:
            if 'quantity' in item:
                order_details += f"- {item['name']} (x{item['quantity']}) @ R{item['amount']:.2f} each 🌟\n"
            else:
                order_details += f"- {item['name']} @ R{item['amount']:.2f} 🌟\n"

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
            f"💰 *Subtotal:* R{final_total - (delivery_charge or 0):.2f} 💸\n"
            f"🚚 *Delivery Charge:* R{delivery_charge or 0:.2f} 🚛\n"
            f"💰 *Total Amount:* R{final_total:.2f} 💳\n"
            f"💳 *Payment Method:* {payment_method} 🏧\n"
            f"----------------------------------------\n"
            f"✨ *Special Note:* {special_note if special_note else 'None'} 📝\n"
            f"⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ⏰"
        )
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        try:
            response = requests.post(TELEGRAM_API_URL, json=payload, timeout=5)
            response.raise_for_status()
            print("Telegram notification sent successfully! 🎉")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send Telegram notification: {e} 😢")

    app.send_telegram_notification = send_telegram_notification

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
            orders = app.db.collection('orders').order_by('order_number', direction=firestore.Query.DESCENDING).limit(1).stream()
            last_order = next(orders, None)
            if last_order:
                last_number = int(last_order.to_dict().get('order_number', '0'))
                return f"{last_number + 1:04d}"
            return "0001"
        except Exception as e:
            print(f"Error generating order number: {e} 😢")
            return "0001"

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
                flash('Database not available. Failed to submit review. 😞', 'error')
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
                if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                    message_text = (
                        f"⭐ *New Review Submitted!*\n"
                        f"----------------------------------------\n"
                        f"📦 *Product:* {product or 'N/A'}\n"
                        f"⭐ *Rating:* {rating} stars\n"
                        f"💬 *Review:* {review}\n"
                        f"👤 *Name:* {name or 'Anonymous'}\n"
                        f"⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ⏰"
                    )
                    payload = {
                        'chat_id': TELEGRAM_CHAT_ID,
                        'text': message_text,
                        'parse_mode': 'Markdown'
                    }
                    response = requests.post(TELEGRAM_API_URL, json=payload, timeout=5)
                    response.raise_for_status()
                    print("Review notification sent to Telegram! 🎉")
                flash('Thank you for your review! Your feedback means the world to us! 🌟', 'success')
            except Exception as e:
                flash(f'Failed to submit review: {str(e)} 😢', 'error')

            return redirect(url_for('rate_us'))
        return render_template('rate_us.html')

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            if not app.db:
                flash('Database not available. Failed to send message. 😞', 'error')
                return redirect(url_for('contact'))

            name = request.form.get('name')
            email = request.form.get('email')
            message = request.form.get('message')

            contact_request = {
                'name': name,
                'email': email,
                'message': message,
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            try:
                app.db.collection('contact_requests').add(contact_request)
                if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                    message_text = (
                        f"📬 *New Contact Message*\n"
                        f"----------------------------------------\n"
                        f"👤 *Name:* {name}\n"
                        f"📧 *Email:* {email}\n"
                        f"💬 *Message:* {message}\n"
                        f"⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ⏰"
                    )
                    payload = {
                        'chat_id': TELEGRAM_CHAT_ID,
                        'text': message_text,
                        'parse_mode': 'Markdown'
                    }
                    response = requests.post(TELEGRAM_API_URL, json=payload, timeout=5)
                    response.raise_for_status()
                    print("Contact message notification sent to Telegram! 🎉")
                flash('Your message has been sent successfully! 🚀', 'success')
            except Exception as e:
                flash(f'Failed to send message: {str(e)} 😢', 'error')

            return redirect(url_for('contact'))
        return render_template('contact.html')

    @app.route('/products')
    def menus():
        category_set = set(product['category'] for product in PRODUCTS)
        ordered_categories = ['Mouthwash Sachets', 'Guest Amenities', 'Oral Care Accessories']
        categories = {cat: {'description': f"Explore our {cat} products for ultimate freshness! 🌟"} for cat in ordered_categories if cat in category_set}
        return render_template('menus.html', categories=categories)

    @app.route('/products/<string:category_name>')
    def show_menu_category(category_name):
        category_name_display = category_name.replace('_', ' ').title()
        items = [p for p in PRODUCTS if p['category'] == category_name_display]

        if category_name_display == 'Mouthwash Sachets':
            single_sachets = [item for item in items if item.get('type', 'single') == 'single']
            boxes = [item for item in items if item.get('type', '') == 'box']
            flavor_order = ['Mint', 'Strawberry Mint', 'Apple', 'Watermelon']
            single_sachets = sorted(single_sachets, key=lambda x: (flavor_order.index(x.get('name', '').split()[0]) if x.get('name', '').split()[0] in flavor_order else len(flavor_order), x.get('name', '')))
            boxes = sorted(boxes, key=lambda x: (flavor_order.index(x.get('name', '').split()[0]) if x.get('name', '').split()[0] in flavor_order else len(flavor_order), x.get('name', '')))
            items = single_sachets + boxes
        else:
            items = sorted(items, key=lambda x: x.get('name', ''))

        return render_template('menu_category.html', category_name=category_name_display, items=items)

    @app.route('/add-to-cart', methods=['POST'])
    def add_to_cart():
        item_id = request.form.get('item_id')
        item_name = request.form.get('item_name')
        item_amount = float(request.form.get('item_amount'))
        quantity = int(request.form.get('quantity', 1))

        if 'cart' not in session:
            session['cart'] = []

        cart_item = {
            'id': item_id,
            'name': item_name,
            'amount': item_amount,
            'quantity': quantity,
            'total': item_amount * quantity
        }

        item_found = False
        for item in session['cart']:
            if item['id'] == item_id:
                item['quantity'] += quantity
                item['total'] = item['amount'] * item['quantity']
                item_found = True
                break

        if not item_found:
            session['cart'].append(cart_item)

        session.modified = True
        flash(f"Added {quantity}x {item_name} to your cart! 🛍️🎉", 'success')
        return redirect(url_for('menus'))

    @app.route('/view-cart')
    def view_cart():
        cart_items = session.get('cart', [])
        total_amount = sum(item['total'] for item in cart_items)
        return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)

    @app.route('/update-cart', methods=['POST'])
    def update_cart():
        item_id = request.form.get('item_id')
        new_quantity = int(request.form.get('quantity', 1))

        if 'cart' in session:
            for item in session['cart']:
                if item['id'] == item_id:
                    if new_quantity > 0:
                        item['quantity'] = new_quantity
                        item['total'] = item['amount'] * new_quantity
                    else:
                        session['cart'].remove(item)
                    break
            session.modified = True
        return redirect(url_for('view_cart'))

    @app.route('/remove-from-cart', methods=['POST'])
    def remove_from_cart():
        item_id = request.form.get('item_id')
        if 'cart' in session:
            session['cart'] = [item for item in session['cart'] if item['id'] != item_id]
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

        subtotal = sum(item['total'] for item in cart_items)
        delivery_charge = 0.0
        total_amount = subtotal

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
                total_amount = subtotal + delivery_charge

            order_number = get_next_order_number()
            order_data = {
                'order_number': order_number,
                'customer_details': customer_details,
                'cart_items': cart_items,
                'subtotal': subtotal,
                'delivery_charge': delivery_charge,
                'total_amount': total_amount,
                'payment_method': payment_method,
                'special_note': special_note,
                'status': 'Pending',
                'timestamp': datetime.now().isoformat()
            }

            try:
                if app.db:
                    app.db.collection('orders').add(order_data)
                app.send_telegram_notification(order_number, cart_items, customer_details, total_amount, delivery_charge, payment_method, special_note)
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

        if session.get('remembered_customer', {}).get('delivery_type') == 'Delivery':
            origin = "27 Parakeet Street, Villa Lisa, Boksburg, 1459"
            delivery_charge = calculate_delivery_charge(origin, session.get('remembered_customer', {}).get('address', ''))
            total_amount = subtotal + delivery_charge

        return render_template('checkout.html', cart_items=cart_items, subtotal=subtotal, delivery_charge=delivery_charge, total_amount=total_amount, remembered_customer=session.get('remembered_customer', {}))

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