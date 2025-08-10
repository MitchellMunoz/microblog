from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from datetime import datetime
from decimal import Decimal

from werkzeug.utils import secure_filename
from flask_babel import _
import os
from flask_login import login_required
from app.finance import bp
from app.finance.config import Donations_Folder, Expense_Folder
from app.finance.utils import load_and_clean, compute_metrics, plot_monthly_totals
from app.finance.models import Receipt  # import your model
from app import db

# Allowed file extensions for receipt uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'csv'}

def allowed_file(filename):
    """
    Check if the file has one of the allowed extensions.
    """
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

@bp.route("/reports", methods=["GET"])
@login_required
def reports():
    # You can extend this to show a static or previously generated report
    return "This is a crappy report"


@bp.route('/expenses', methods=['GET', 'POST'])
@login_required
def receipts():
    filename = None

    if request.method == 'POST':
        file = request.files.get('file')
        merchant = request.form.get('merchant')
        date = request.form.get('date')
        category = request.form.get('category')
        gtq_amount = request.form.get('gtq_amount')
        usd_amount = request.form.get('usd_amount')
        memo = request.form.get('memo')

        if not file or file.filename == '':
            flash(_('No file selected.'))
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash(_('Invalid file type.'))
            return redirect(request.url)

        os.makedirs(Expense_Folder, exist_ok=True)
        filename = secure_filename(file.filename)
        filepath = os.path.join(Expense_Folder, filename)
        file.save(filepath)

        gtq_amount = Decimal(gtq_amount) if gtq_amount else Decimal('0.00')
        usd_amount = Decimal(usd_amount) if usd_amount else Decimal('0.00')

        date_obj = datetime.strptime(date, "%Y-%m-%d")
        receipt = Receipt(
            merchant=merchant,
            upload_date=date_obj,
            gtq_amount=gtq_amount,
            usd_amount=usd_amount,
            memo=memo,
            category=category,
            receipt_file=filename,
        )
        db.session.add(receipt)
        db.session.commit()

        flash(_('Receipt "%(name)s" uploaded successfully.', name=filename))
        return redirect(url_for('finance.receipts'))

    # GET: show upload form and list existing receipts from DB
    receipts = Receipt.query.order_by(Receipt.upload_date.desc()).all()
    return render_template(
        'finance/expenses.html',
        receipts=receipts
    )

@bp.route('/uploads/<filename>')
def uploaded_file(filename):
    # serve uploaded expense files
    return send_from_directory(Expense_Folder, filename)

@login_required
@bp.route('/donations', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash(_('No file part in the request.'))
            return redirect(request.url)
        filename = secure_filename(file.filename)
        if file.filename == '':
            flash(_('No file selected.'))
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash(_('Invalid file type.'))
            return redirect(request.url)
        os.makedirs(Donations_Folder, exist_ok=True)
        filepath = os.path.join(Donations_Folder, filename)
        file.save(filepath)
        df = load_and_clean(filepath)
        metrics = compute_metrics(df)
        chart_name = f"{os.path.splitext(filename)[0]}_monthly.png"
        chart_dir = os.path.join(current_app.static_folder, 'charts')
        os.makedirs(chart_dir, exist_ok=True)
        chart_path = os.path.join(chart_dir, chart_name)
        plot_monthly_totals(metrics['monthly_totals'], chart_path)
        chart_url = url_for('static', filename=f'charts/{chart_name}')
        return render_template(
            'finance/report.html',
            filename=filename,
            chart_url=chart_url,
            **metrics
        )
    return render_template('finance/upload.html', title=_('Upload a file'))
