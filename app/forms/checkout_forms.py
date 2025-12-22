"""
Checkout Forms - Forms for checkout process.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp


class CheckoutForm(FlaskForm):
    """Form for checkout information."""
    
    name = StringField(
        'Full Name',
        validators=[
            DataRequired(message='Name is required'),
            Length(min=2, max=100, message='Name must be between 2 and 100 characters')
        ]
    )
    
    phone = StringField(
        'Phone Number',
        validators=[
            DataRequired(message='Phone number is required'),
            Regexp(
                r'^01[0-9]{9}$',
                message='Please enter a valid Bangladeshi phone number (e.g., 01712345678)'
            )
        ]
    )
    
    address = TextAreaField(
        'Delivery Address',
        validators=[
            DataRequired(message='Address is required'),
            Length(min=10, max=500, message='Address must be between 10 and 500 characters')
        ]
    )
    
    submit = SubmitField('Place Order')
