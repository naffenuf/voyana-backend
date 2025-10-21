"""
Application entry point.

For development: flask run --reload
For production: gunicorn run:app
"""
import os
from app import create_app

# Create Flask application instance
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
