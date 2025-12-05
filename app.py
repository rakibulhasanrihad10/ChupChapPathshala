from flask import Flask, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from dataclasses import dataclass
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///chupchappathshala"
app.config["SECRET"] = "blah"
db = SQLAlchemy(app)
@dataclass
class Book(db.Model): # the type annotations are necessary for jsonify
    id: int = db.Column(db.Integer, primary_key = True)
    title: str = db.Column(db.String(20), unique= False, nullable = False)
    author: str = db.Column(db.String(20), unique=False, nullable = False)

books = [
    Book(title="book1",author="Author1"),
    Book(title="book2",author="Author2"),
    Book(title="book3",author="Author3"),
]


def get_items():
    return books

@app.route("/")
def index():
    return """
    <h1> routes </h1>
    <ul>
    <li><a href="/inventory">/inventory</a></li>
    </ul>
    """

@app.route("/inventory")
def inventory():
    return render_template("inventory.book.html", items = get_items())
