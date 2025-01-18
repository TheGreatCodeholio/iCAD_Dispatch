import logging

from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template, current_app, session

from lib.user_module import authenticate_user, user_change_password
from routes.decorators import login_required

auth = Blueprint('auth', __name__)
module_logger = logging.getLogger('icad_dispatch.auth')


@auth.route('/login', methods=['POST'])
def auth_login():
    username = request.form['username']
    password = request.form['password']
    if not username or not password:
        flash('Username and Password Required', 'danger')
        return redirect(url_for('base_site.base_site_index'))

    auth_result = authenticate_user(current_app.config['db'], username, password)
    flash(auth_result["message"], 'success' if auth_result["success"] else 'danger')
    return redirect(
        url_for('admin.admin_dashboard') if auth_result["success"] else url_for('base_site.base_site_index'))


@auth.route("/logout")
def auth_logout():
    session.clear()
    return redirect(url_for('base_site.base_site_index'))


@auth.route("/change_password")
@login_required
def auth_change_password():
    try:
        # Extract JSON data from request
        request_form = request.form
        if not request_form:
            message = "No data provided."
            module_logger.error(message)
            flash(message, 'danger')
            return redirect(url_for('admin.admin_dashboard'))

        current_password = request_form.get("currentPassword")
        new_password = request_form.get("newPassword")

        if not new_password or not new_password:
            message = "No password provided or empty string."
            module_logger.error(message)
            flash(message, 'danger')
            return redirect(url_for('admin.admin_dashboard'))

        result = user_change_password(current_app.config['db'], "admin", current_password, new_password)

        module_logger.debug(result.get("message"))
        flash(result.get("message"), 'success' if result.get("success") else 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    except Exception as e:
        message = f"Unexpected error: {e}"
        module_logger.error(message)
        flash(message, 'danger')
        return redirect(url_for('admin.admin_dashboard'))
