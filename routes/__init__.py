# routes/__init__.py

from flask import Flask
from routes.middleware import log_ip, inject_csrf_token
from routes.base_site.base_site import base_site  # Import the Blueprint from base_site

def register_middlewares(app: Flask):
    """Registers global middlewares for the Flask app."""
    app.before_request(log_ip)  # Log IP address before every request
    app.context_processor(inject_csrf_token)  # Inject CSRF token into templates