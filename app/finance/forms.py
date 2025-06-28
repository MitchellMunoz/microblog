from flask_wtf import FlaskForm
from wtforms import StringField, DateField, FileField, DecimalField, TextAreaField, SelectField
from wtforms.validators import DataRequired, NumberRange
from flask_wtf.file import FileAllowed, FileRequired


CATEGORIES = [
    ('fees', 'Fees & Adjustments'),
    ('shopping', 'Shopping'),
    ('prof_services', 'Professional Services'),
    ('home', 'Home'),
    ('food_drink', 'Food & Drink'),
    ('groceries', 'Groceries'),
    ('bills_utils', 'Bills & Utilities'),
    ('personal', 'Personal'),
    ('gas', 'Gas'),
    ('education', 'Education'),
    ('entertainment', 'Entertainment'),
    ('health', 'Health & Wellness'),
    ('travel', 'Travel'),
    ('gifts', 'Gifts & Donations'),
    ('auto', 'Automotive'),
]

class ReceiptForm(FlaskForm):
    merchant = StringField("Merchant", validators=[DataRequired()])
    date = DateField("Date", validators=[DataRequired()])
    amount = DecimalField("Amount", places=2, rounding=None, validators=[DataRequired(), NumberRange(min=0)])
    currency = SelectField(
        "Currency",
        choices=[("GTQ", "GTQ"), ("USD", "$")],
        default="GTQ",
        validators=[DataRequired()]
    )
    memo = TextAreaField("Memo")  # Optional field
    category = SelectField("Category", choices=CATEGORIES, validators=[DataRequired()])
    receipt = FileField("Receipt Image", validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'pdf'], "Images or PDF only!"),
        FileRequired("File was empty!")
    ])
