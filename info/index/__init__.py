from flask import Blueprint

blue_index = Blueprint("index", __name__)
from . import index

