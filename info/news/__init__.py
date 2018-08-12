from flask import Blueprint

blue_news = Blueprint("news", __name__, url_prefix="/news")
from . import view