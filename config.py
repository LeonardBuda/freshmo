import os
import json

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-very-secret-key-replace-this'
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Firebase Configuration
    FIREBASE_CREDENTIALS = os.environ.get('FIREBASE_CREDENTIALS')
    if FIREBASE_CREDENTIALS:
        try:
            FIREBASE_CONFIG = json.loads(FIREBASE_CREDENTIALS)
        except json.JSONDecodeError:
            print("Error: FIREBASE_CREDENTIALS environment variable is not valid JSON.")
            FIREBASE_CONFIG = None
    else:
        # Fallback for local development if not using environment variable
        # IMPORTANT: In production, always use environment variables for security!
        FIREBASE_ADMIN_SDK_PATH = os.path.join(os.path.dirname(__file__), 'freshmo-14493-firebase-adminsdk-fbsvc-cd258e541d.json')
        if os.path.exists(FIREBASE_ADMIN_SDK_PATH):
            with open(FIREBASE_ADMIN_SDK_PATH, 'r') as f:
                FIREBASE_CONFIG = json.load(f)
        else:
            FIREBASE_CONFIG = None
            print("Warning: Firebase Admin SDK JSON file not found. Ensure FIREBASE_CREDENTIALS env var is set or file exists.")

    # Telegram Bot Configuration (for notifications)
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    ENV = 'development'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    ENV = 'production'
    # Ensure SECRET_KEY and FIREBASE_CREDENTIALS are set in production environment variables