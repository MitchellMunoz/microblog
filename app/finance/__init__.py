from flask import Blueprint


bp = Blueprint('finance', __name__, template_folder='templates', url_prefix='/finance')
from app.finance import routes
