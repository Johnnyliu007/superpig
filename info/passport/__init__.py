from flask import Blueprint


blue_passport = Blueprint("passport", __name__, url_prefix="/passport")
from . import view