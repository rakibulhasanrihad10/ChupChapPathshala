from flask import Blueprint
bp = Blueprint('main', __name__)
from app.main import routes, inventory_routes, cart_routes, checkout_routes, restock_form
