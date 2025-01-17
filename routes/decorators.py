from functools import wraps

import jwt
from flask import redirect, url_for, session, request, jsonify, current_app, render_template, flash


def csrf_protect(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE']:
            token = session.get('_csrf_token', None)
            if not token or token != request.form.get('_csrf_token'):
                flash('Form submission failed. Please try again.', 'danger')
                return redirect(request.referrer or '/')
        return func(*args, **kwargs)
    return wrapper


def token_required(f):
    @wraps(f)
    def wrapped_function(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"message": "Access Denied"}), 401

        try:
            secret_key = current_app.config.get('SECRET_KEY')
            payload = jwt.decode(token.split(" ")[1], secret_key, algorithms=["HS256"])

            # Validate the user's IP address
            ip_addresses = payload.get('ip', [])
            if not isinstance(ip_addresses, list):
                ip_addresses = [ip_addresses]  # Handle old tokens with a single IP

            if request.remote_addr not in ip_addresses:
                return jsonify({"message": "Access Denied: IP address mismatch"}), 401

            kwargs['user_id'] = payload.get('user_id')  # Pass user_id to the route

        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Token is invalid"}), 403

        return f(*args, **kwargs)

    return wrapped_function


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        authenticated = session.get('authenticated')
        if not authenticated:
            current_app.config['logger'].debug(f"Redirecting User: Current session data: {dict(session)}")
            return redirect(url_for('base_site.base_site_index'))
        else:
            current_app.config['logger'].debug(f"User Authorized: Current session data: {dict(session)}")

        return func(*args, **kwargs)

    return wrapper
