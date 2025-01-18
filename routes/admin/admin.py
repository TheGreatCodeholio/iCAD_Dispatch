import logging

from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template, current_app, session

from routes.decorators import login_required

admin = Blueprint('admin', __name__)
module_logger = logging.getLogger('icad_dispatch.admin')

@admin.route('/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    return render_template("admin_dashboard.html")