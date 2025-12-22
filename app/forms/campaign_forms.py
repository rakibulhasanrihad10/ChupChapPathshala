"""
Campaign Forms - Forms for campaign management.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SubmitField, BooleanField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, URL, Optional, Length


class CampaignForm(FlaskForm):
    """Form for creating and editing campaigns."""
    
    title = StringField(
        'Campaign Title',
        validators=[
            DataRequired(message='Title is required'),
            Length(max=200, message='Title must be less than 200 characters')
        ]
    )
    
    description = TextAreaField(
        'Description',
        validators=[
            Optional(),
            Length(max=500, message='Description must be less than 500 characters')
        ]
    )
    
    image_url = StringField(
        'Image URL',
        validators=[
            Optional(),
            URL(message='Please enter a valid URL')
        ]
    )
    
    image_file = FileField(
        'Upload Image',
        validators=[
            FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
        ]
    )
    
    button_text = StringField(
        'Button Text',
        validators=[
            Optional(),
            Length(max=50, message='Button text must be less than 50 characters')
        ]
    )
    
    button_link = StringField(
        'Button Link',
        validators=[
            Optional(),
            Length(max=200, message='Button link must be less than 200 characters')
        ]
    )
    
    start_time = DateTimeLocalField(
        'Start Time',
        format='%Y-%m-%dT%H:%M',
        validators=[Optional()]
    )
    
    end_time = DateTimeLocalField(
        'End Time',
        format='%Y-%m-%dT%H:%M',
        validators=[Optional()]
    )
    
    is_active = BooleanField('Active')
    
    submit = SubmitField('Save Campaign')
