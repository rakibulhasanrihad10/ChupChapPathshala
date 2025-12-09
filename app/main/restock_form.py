from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class RestockForm(FlaskForm):
    quantity = IntegerField(
        "Quantity to Add",
        validators=[DataRequired(), NumberRange(min=1, message="Must be at least 1")]
    )
    submit = SubmitField("Restock")
