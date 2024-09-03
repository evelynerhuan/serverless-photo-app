#!/venv/bin/python
from app import webapp
import os

if __name__ == "__main__":
    # Use different configurations for development and production
    environment = os.environ.get('FLASK_ENV', 'development')
    
    if environment == 'development':
        webapp.run(host='127.0.0.1', port=5000, debug=True)
    else:
        webapp.run(host='0.0.0.0', port=8000)