from flask import Blueprint


blue_user = Blueprint("user", __name__, url_prefix="/user")
from . import view

