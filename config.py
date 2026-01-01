import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    # Legacy SQL settings retained for compatibility if needed
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///aura.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # MongoDB Atlas configuration
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'aura_db')
    # Local MongoDB: no TLS needed
    MONGODB_TLS = False
    MONGODB_TLS_ALLOW_INVALID_CERTIFICATES = False

    # Mail (optional; alerts will still be logged without mail)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME', ''))
