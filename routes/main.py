from flask import Blueprint, render_template, url_for, request, flash, current_app, redirect
import time
import json # Import json for parsing FIREBASE_CREDENTIALS if needed for direct use in route (though config handles it)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/home')
def home():
    """Renders the home page."""
    return render_template('home.html')

@main_bp.route('/about')
def about():
    """Renders the about page."""
    return render_template('about.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Renders the contact page and handles contact form submission."""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        subject = request.form.get('subject')
        message = request.form.get('message')

        if not name or not email or not subject or not message:
            flash('Please fill in all required fields.', 'error')
            return render_template('contact.html', name=name, email=email, phone=phone, subject=subject, message=message)

        try:
            # Construct a detailed message for Telegram notification
            telegram_message = (
                f"📧 New Contact Form Submission! 📧\n\n"
                f"Name: {name}\n"
                f"Email: {email}\n"
                f"Phone: {phone or 'N/A'}\n"
                f"Subject: {subject}\n\n"
                f"Message:\n{message}"
            )
            current_app.send_telegram_notification(
                order_number=None,
                cart_items=[],
                customer_details={},
                final_total=0,
                payment_method=None,
                special_note=telegram_message
            )
            flash('Your message has been sent successfully! We will get back to you soon. 🚀', 'success')
            return redirect(url_for('main.contact'))
        except Exception as e:
            flash(f'Failed to send your message: {str(e)} 😞 Please try again.', 'error')
            return render_template('contact.html', name=name, email=email, phone=phone, subject=subject, message=message)
    return render_template('contact.html')

@main_bp.route('/faqs')
def faqs():
    """Renders the FAQs page."""
    return render_template('faqs.html')

@main_bp.route('/gallery')
def gallery():
    """Renders the gallery page."""
    return render_template('gallery.html')

@main_bp.route('/track_order', methods=['GET', 'POST'])
def track_order():
    """Handles order tracking requests."""
    if request.method == 'POST':
        order_number = request.form.get('order_number')
        phone = request.form.get('phone')

        if not order_number and not phone:
            flash('Please provide an Order Number or Phone Number to track your order.', 'error')
            return render_template('track_order.html')

        try:
            # In a real application, you would query Firestore here to get order status
            # For now, we'll just send a notification and simulate success.
            # Example Firestore query (conceptual):
            # orders_ref = current_app.db.collection('orders')
            # query = orders_ref.where('order_number', '==', order_number)
            # if phone:
            #     query = query.where('customer_details.phone', '==', phone)
            # docs = query.get()
            # if docs:
            #     # Process order status
            #     flash(f"Order {order_number} status: Processing. We'll update you soon!", 'success')
            # else:
            #     flash("Order not found. Please double-check your details.", 'error')

            # Send Telegram notification
            message = (
                f"New Order Tracking Request 📬\n\n"
                f"Order Number: {order_number or 'N/A'} 🌟\n"
                f"Phone: {phone or 'N/A'} 📱\n"
                f"Time: {time.strftime('%I:%M %p SAST, %B %d, %Y')} ⏰\n\n"
                f"Please follow up! 🚨"
            )
            current_app.send_telegram_notification(order_number=None, cart_items=[], customer_details={}, final_total=0, payment_method=None, special_note=message)

            flash("Request submitted! We’ll get back to you soon. 🚀", 'success')
            return redirect(url_for('main.track_order'))
        except Exception as e:
            flash(f"Tracking request failed: {str(e)} 😞", 'error')
            return render_template('track_order.html')
    return render_template('track_order.html')

@main_bp.route('/rate_us')
def rate_us():
    """Renders the rate us page."""
    return render_template('rate_us.html')

@main_bp.route('/store_location')
def store_location():
    """Renders the store location page."""
    return render_template('store_location.html')

# Placeholder route for Adsterra Native Banner ads (if needed, otherwise remove)
@main_bp.route('/ads/adsterra_banner')
def adsterra_banner():
    """Renders a placeholder for Adsterra Native Banner ads."""
    return render_template('adsterra_banner.html')
