from app import db

class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    merchant = db.Column(db.String(100), nullable=False)
    upload_date = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    gtq_amount = db.Column(db.Numeric(scale=2), nullable=False)
    usd_amount = db.Column(db.Numeric(scale=2), nullable=False)
    memo = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    receipt_file = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<Receipt {self.id} {self.merchant} {self.amount} {self.currency}>"