import os
from flask import Flask
from flask_mail import Mail

# Function to create and configure the Flask application
def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')

    # Use environment variables to manage sensitive information
    app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

    # Configuration for Flask-Mail
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = os.environ.get('MAIL_PORT', 465)
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your_email@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your_password')
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', False)
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', True)

    # Initialize Flask-Mail
    mail = Mail(app)

    # Import routes and other components after app is created
    with app.app_context():
        from app import routes
        from app import main
        from app import image

    return app

# Create an instance of the Flask app
webapp = create_app()