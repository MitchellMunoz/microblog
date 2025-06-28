from flask import Blueprint

bp = Blueprint('mission', __name__)

from app.mission import routes
