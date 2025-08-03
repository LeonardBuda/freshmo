from firebase_admin import firestore
from flask import current_app

class FirestoreService:
    def __init__(self):
        # Ensure Firebase app is initialized before getting the client
        if not hasattr(current_app, 'db'):
            # This should ideally be handled during app creation, but as a fallback
            # or for direct script execution, ensure db is accessible.
            # In a Flask app context, current_app.db should already be set.
            # For this service, we'll assume current_app.db is available.
            pass
        self.db = firestore.client()

    def get_products(self):
        """Fetches all products from Firestore."""
        products_ref = self.db.collection('products')
        docs = products_ref.stream()
        products = []
        for doc in docs:
            product_data = doc.to_dict()
            product_data['id'] = doc.id # Add document ID to the data
            products.append(product_data)
        return products

    def get_product_by_id(self, product_id):
        """Fetches a single product by its ID."""
        product_ref = self.db.collection('products').document(product_id)
        doc = product_ref.get()
        if doc.exists:
            product_data = doc.to_dict()
            product_data['id'] = doc.id
            return product_data
        return None

    def add_product(self, product_data):
        """Adds a new product to Firestore."""
        products_ref = self.db.collection('products')
        # Use a specific ID if provided, otherwise let Firestore generate one
        if 'id' in product_data:
            doc_id = product_data.pop('id')
            products_ref.document(doc_id).set(product_data)
            return doc_id
        else:
            doc_ref = products_ref.add(product_data)
            return doc_ref[1].id # Returns the ID of the new document

    def update_product(self, product_id, updates):
        """Updates an existing product in Firestore."""
        product_ref = self.db.collection('products').document(product_id)
        product_ref.update(updates)

    def delete_product(self, product_id):
        """Deletes a product from Firestore."""
        self.db.collection('products').document(product_id).delete()

    def add_order(self, order_data):
        """Adds a new order to Firestore."""
        orders_ref = self.db.collection('orders')
        doc_ref = orders_ref.add(order_data)
        return doc_ref[1].id

    def get_order_by_id(self, order_id):
        """Fetches a single order by its ID."""
        # Note: If order_id is the auto-generated Firestore ID, this works.
        # If it's a custom order_number, you'd need to query:
        # query = self.db.collection('orders').where('order_number', '==', order_id)
        # docs = query.stream()
        # for doc in docs: return doc.to_dict()
        order_ref = self.db.collection('orders').document(order_id)
        doc = order_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None

    # Add more methods as needed for users, reviews, etc.
