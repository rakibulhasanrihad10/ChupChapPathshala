from app.main import bp
from app.models import Book
from flask import render_template

#@bp.route("/featured")
def featured():
    return render_template("featured.html")

def fetch_most_sold(number: int):
    return Book.query.order_by(Book.stock_sold.desc()).limit(number).all()
