from flask_wtf import FlaskForm
from wtforms import StringField, DateField, FileField, DecimalField
from wtforms.validators import DataRequired

class ReceiptForm(FlaskForm):
    merchant = StringField("Merchant", validators=[DataRequired()]
    date = DateField("Date", validators=[DataRequired()]
    amount = DecimalField("Amount", places=2, rounding=None, validators = [DataRequired(), NumberRange(min=0)])
    #memo
    #category
    #receipt
