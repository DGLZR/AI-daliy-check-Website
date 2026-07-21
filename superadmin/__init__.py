from flask import Blueprint, render_template

superadmin_bp = Blueprint('superadmin', __name__, template_folder='templates')

@superadmin_bp.route('/superadmin')
def superadmin_page():
    return render_template('index.html')