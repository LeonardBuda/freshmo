import os
import json
from firebase_admin import credentials, initialize_app, firestore
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# --- Firebase Initialization (similar to app.py but for a script) ---
# This block tries to load Firebase credentials from an environment variable first.
# If not found, it looks for a local JSON file.
firebase_credentials = os.environ.get('FIREBASE_CREDENTIALS')
firebase_config = None

if firebase_credentials:
    try:
        firebase_config = json.loads(firebase_credentials)
    except json.JSONDecodeError:
        print("Error: FIREBASE_CREDENTIALS environment variable is not valid JSON.")
else:
    # UPDATED: Changed the default Firebase credential file path to match your file
    cred_path = os.path.join(os.path.dirname(__file__), 'freshmo-14493-firebase-adminsdk-fbsvc-cd258e541d.json')
    if os.path.exists(cred_path):
        with open(cred_path, 'r') as f:
            firebase_config = json.load(f)
    else:
        print("Warning: Firebase Admin SDK JSON file not found. Ensure FIREBASE_CREDENTIALS env var is set or file exists.")

if firebase_config:
    try:
        cred = credentials.Certificate(firebase_config)
        initialize_app(cred)
        print("Firebase Admin SDK initialized successfully for data population.")
    except Exception as e:
        print(f"Error initializing Firebase Admin SDK for data population: {e}")
        exit("Exiting: Firebase initialization failed.")
else:
    exit("Exiting: Firebase configuration missing. Cannot populate data.")

db = firestore.client()
# --- End Firebase Initialization ---

# Freshmo Product Data based on Freshmo.docx and general e-commerce needs
# UPDATED: Image URLs to match your available images (image1.jpg to image8.jpg)
products_data = [
    {
        "id": "freshmo_peppermint_30sachet_box",
        "name": "Freshmo Mouthwash - Peppermint (Box of 30)",
        "slug": "peppermint-mouthwash-30-sachet-box",
        "flavor": "Peppermint",
        "packaging_type": "Sachet Box",
        "unit_size": "10ml",
        "units_per_pack": 30,
        "description": "Our signature alcohol-free peppermint mouthwash in a convenient box of 30 single-use sachets. Perfect for daily freshness and combating bad breath on the go.",
        "price_zar": 150.00,
        "image_urls": [
            "/static/images/image1.jpg", # Using new image
            "/static/images/sachet_box.jpg" # Keeping specific image
        ],
        "stock_quantity": 500,
        "is_available": True,
        "category": "Mouthwash Sachets",
        "features": [
            "Alcohol-free", "SABS Tested", "2-year shelf life", "Trademarked",
            "Formulated by Prof. David Katerere", "Freshness on the Go",
            "Combats plaque and bad breath", "Promotes healthy gums"
        ],
        "brand": "Freshmo Brands",
        "proudly_sa_endorsed": True,
        "is_new_flavor": False,
        "is_travel_pack": False
    },
    {
        "id": "freshmo_spearmint_30sachet_box",
        "name": "Freshmo Mouthwash - Spearmint (Box of 30)",
        "slug": "spearmint-mouthwash-30-sachet-box",
        "flavor": "Spearmint",
        "packaging_type": "Sachet Box",
        "unit_size": "10ml",
        "units_per_pack": 30,
        "description": "Experience the cool, refreshing taste of spearmint with our alcohol-free mouthwash. This box of 30 sachets ensures you always have freshness at hand.",
        "price_zar": 150.00,
        "image_urls": [
            "/static/images/image2.jpg", # Using new image
            "/static/images/sachet_box.jpg" # Keeping specific image
        ],
        "stock_quantity": 450,
        "is_available": True,
        "category": "Mouthwash Sachets",
        "features": [
            "Alcohol-free", "SABS Tested", "2-year shelf life", "Trademarked",
            "Formulated by Prof. David Katerere", "Freshness on the Go",
            "Combats plaque and bad breath", "Promotes healthy gums"
        ],
        "brand": "Freshmo Brands",
        "proudly_sa_endorsed": True,
        "is_new_flavor": False,
        "is_travel_pack": False
    },
    {
        "id": "freshmo_peppermint_single_sachet",
        "name": "Freshmo Mouthwash - Peppermint (Single Sachet)",
        "slug": "peppermint-mouthwash-single-sachet",
        "flavor": "Peppermint",
        "packaging_type": "Single Sachet",
        "unit_size": "10ml",
        "units_per_pack": 1,
        "description": "A single 10ml sachet of our invigorating peppermint mouthwash. Perfect for trying out or for ultimate portability.",
        "price_zar": 6.99,
        "image_urls": [
            "/static/images/image3.jpg", # Using new image
            "/static/images/sachet_in_hand.jpg" # Keeping specific image
        ],
        "stock_quantity": 1000,
        "is_available": True,
        "category": "Mouthwash Sachets",
        "features": [
            "Alcohol-free", "SABS Tested", "2-year shelf life", "Trademarked",
            "Formulated by Prof. David Katerere", "Freshness on the Go"
        ],
        "brand": "Freshmo Brands",
        "proudly_sa_endorsed": True,
        "is_new_flavor": False,
        "is_travel_pack": False
    },
    {
        "id": "freshmo_spearmint_single_sachet",
        "name": "Freshmo Mouthwash - Spearmint (Single Sachet)",
        "slug": "spearmint-mouthwash-single-sachet",
        "flavor": "Spearmint",
        "packaging_type": "Single Sachet",
        "unit_size": "10ml",
        "units_per_pack": 1,
        "description": "A single 10ml sachet of our cool spearmint mouthwash, providing instant freshness wherever you are.",
        "price_zar": 6.99,
        "image_urls": [
            "/static/images/image4.jpg", # Using new image
            "/static/images/sachet_in_hand.jpg" # Keeping specific image
        ],
        "stock_quantity": 900,
        "is_available": True,
        "category": "Mouthwash Sachets",
        "features": [
            "Alcohol-free", "SABS Tested", "2-year shelf life", "Trademarked",
            "Formulated by Prof. David Katerere", "Freshness on the Go"
        ],
        "brand": "Freshmo Brands",
        "proudly_sa_endorsed": True,
        "is_new_flavor": False,
        "is_travel_pack": False
    },
    {
        "id": "freshmo_biodegradable_toothbrush",
        "name": "Freshmo Biodegradable Toothbrush",
        "slug": "biodegradable-toothbrush",
        "flavor": "N/A",
        "packaging_type": "Single Pack",
        "unit_size": "1 unit",
        "units_per_pack": 1,
        "description": "An eco-friendly biodegradable toothbrush, perfect for sustainable oral care.",
        "price_zar": 35.00,
        "image_urls": [
            "/static/images/biodegradable_toothbrush.jpg" # Keeping specific image
        ],
        "stock_quantity": 200,
        "is_available": True,
        "category": "Oral Care Accessories",
        "features": ["Eco-friendly", "Biodegradable"],
        "brand": "Freshmo Brands",
        "proudly_sa_endorsed": True,
        "is_new_flavor": False,
        "is_travel_pack": False
    },
    {
        "id": "freshmo_organic_mouthwash_bottle",
        "name": "Freshmo Organic Mouthwash (Bottle)",
        "slug": "organic-mouthwash-bottle",
        "flavor": "Natural Mint", # Assuming a natural mint flavor for organic
        "packaging_type": "Bottle",
        "unit_size": "250ml",
        "units_per_pack": 1,
        "description": "Our organic mouthwash in a convenient bottle, made with natural ingredients for a gentle yet effective clean.",
        "price_zar": 80.00,
        "image_urls": [
            "/static/images/organic_mouthwash_bottle.jpg" # Keeping specific image
        ],
        "stock_quantity": 150,
        "is_available": True,
        "category": "Oral Care Accessories",
        "features": ["Organic", "Natural Ingredients", "Alcohol-free"],
        "brand": "Freshmo Brands",
        "proudly_sa_endorsed": True,
        "is_new_flavor": False,
        "is_travel_pack": False
    },
    {
        "id": "freshmo_guest_amenity_basic_kit",
        "name": "Freshmo Guest Amenity Kit (Basic)",
        "slug": "guest-amenity-basic-kit",
        "flavor": "Assorted",
        "packaging_type": "Kit",
        "unit_size": "N/A",
        "units_per_pack": 1,
        "description": "A basic guest amenity kit including a Freshmo mouthwash sachet and a toothbrush. Ideal for hotels and guesthouses.",
        "price_zar": 45.00,
        "image_urls": [
            "/static/images/image5.jpg" # Using new image
        ],
        "stock_quantity": 300,
        "is_available": True,
        "category": "Guest Amenities",
        "features": ["Convenient", "Travel-friendly", "Hospitality solution"],
        "brand": "Freshmo Brands",
        "proudly_sa_endorsed": True,
        "is_new_flavor": False,
        "is_travel_pack": False
    },
    {
        "id": "freshmo_guest_amenity_premium_kit",
        "name": "Freshmo Guest Amenity Kit (Premium)",
        "slug": "guest-amenity-premium-kit",
        "flavor": "Assorted",
        "packaging_type": "Kit",
        "unit_size": "N/A",
        "units_per_pack": 1,
        "description": "A premium guest amenity kit featuring Freshmo mouthwash sachets, a toothbrush, and other toiletries. Perfect for a luxurious stay.",
        "price_zar": 75.00,
        "image_urls": [
            "/static/images/image6.jpg" # Using new image
        ],
        "stock_quantity": 250,
        "is_available": True,
        "category": "Guest Amenities",
        "features": ["Premium", "Comprehensive", "Hospitality solution"],
        "brand": "Freshmo Brands",
        "proudly_sa_endorsed": True,
        "is_new_flavor": False,
        "is_travel_pack": False
    },
    {
        "id": "freshmo_strawberry_mint_30sachet_box_future",
        "name": "Freshmo Mouthwash - Strawberry Mint (Box of 30)",
        "slug": "strawberry-mint-mouthwash-30-sachet-box",
        "flavor": "Strawberry Mint",
        "packaging_type": "Sachet Box",
        "unit_size": "10ml",
        "units_per_pack": 30,
        "description": "Coming Soon! A delightful blend of sweet strawberry and refreshing mint in our alcohol-free mouthwash sachets.",
        "price_zar": 160.00,
        "image_urls": [
            "/static/images/image7.jpg" # Using new image for future product
        ],
        "stock_quantity": 0,
        "is_available": False, # Mark as not available yet
        "category": "Mouthwash Sachets",
        "features": [
            "Alcohol-free", "SABS Tested", "2-year shelf life", "Trademarked",
            "Formulated by Prof. David Katerere", "Freshness on the Go",
            "New Flavor"
        ],
        "brand": "Freshmo Brands",
        "proudly_sa_endorsed": True,
        "is_new_flavor": True,
        "is_travel_pack": False
    },
    {
        "id": "freshmo_apple_30sachet_box_future",
        "name": "Freshmo Mouthwash - Apple (Box of 30)",
        "slug": "apple-mouthwash-30-sachet-box",
        "flavor": "Apple",
        "packaging_type": "Sachet Box",
        "unit_size": "10ml",
        "units_per_pack": 30,
        "description": "Coming Soon! A crisp and refreshing apple-flavored mouthwash in our convenient sachet format.",
        "price_zar": 160.00,
        "image_urls": [
            "/static/images/image8.jpg" # Using new image for future product
        ],
        "stock_quantity": 0,
        "is_available": False,
        "category": "Mouthwash Sachets",
        "features": [
            "Alcohol-free", "SABS Tested", "2-year shelf life", "Trademarked",
            "Formulated by Prof. David Katerere", "Freshness on the Go",
            "New Flavor"
        ],
        "brand": "Freshmo Brands",
        "proudly_sa_endorsed": True,
        "is_new_flavor": True,
        "is_travel_pack": False
    }
]

def populate_products():
    """Populates the 'products' collection in Firestore with Freshmo product data."""
    products_ref = db.collection('products')
    batch = db.batch()
    
    print("Checking for existing products and populating Firestore...")
    
    for product in products_data:
        doc_id = product['id']
        doc_ref = products_ref.document(doc_id)
        
        # Check if document already exists to avoid overwriting if not intended
        existing_doc = doc_ref.get()
        if existing_doc.exists:
            # UPDATED: If product exists, update it with the new image URLs and other data
            batch.update(doc_ref, product)
            print(f"Updated product: {product['name']} (ID: {doc_id}) with new data.")
        else:
            batch.set(doc_ref, product)
            print(f"Added product: {product['name']} (ID: {doc_id})")
            
    try:
        batch.commit()
        print("Firestore population complete.")
    except Exception as e:
        print(f"An error occurred during Firestore batch commit: {e}")

if __name__ == '__main__':
    populate_products()