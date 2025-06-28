from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from werkzeug.utils import secure_filename
from flask_babel import _
import os
from flask_login import login_required
from app.finance import bp
from app import db
from app.finance.config import Expense_Folder
from app.finance.forms import ReceiptForm
from app.finance.models import Receipt  # Import your SQLAlchemy model

# Allowed file extensions for receipts
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'csv'}

def allowed_file(filename):
    """Check if the file has one of the allowed extensions."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/expenses', methods=['GET', 'POST'])
@login_required
def receipts():
    form = ReceiptForm()

    # ---------- 1) Handle upload ----------
    if request.method == "POST" and form.validate_on_submit():
        file = form.receipt.data
        if file and allowed_file(file.filename):
            # unique & safe filename
            filename = secure_filename(file.filename)
            os.makedirs(Expense_Folder, exist_ok=True)
            file.save(os.path.join(Expense_Folder, filename))
            FX = 7.75
            entered_amt = form.amount.data
            if form.currency.data == "GTQ":
                gtq = entered_amt
                usd = entered_amt / FX
            else:                      # USD entered
                gtq = entered_amt * FX
                usd = entered_amt
            # create DB row
            new_receipt = Receipt(
                receipt_file = filename,
                merchant = form.merchant.data,
                amount = form.amount.data,
                currency =form.currency.data,
                gtq_amount = gtq,
                usd_amount = usd,
                memo = form.memo.data,
                category = form.category.data,
            )
            db.session.add(new_receipt)
            db.session.commit()

            flash(_('Receipt "%(name)s" uploaded successfully.', name=filename))
            return redirect(url_for('finance.receipts'))

        flash(_('No file selected or invalid file type.'))
        return redirect(request.url)

    # ---------- 2) GET: pull all saved receipts ----------
    receipts = (Receipt
                .query
                .order_by(Receipt.upload_date.desc())
                .all())

    return render_template(
        "finance/expenses.html",
        form=form,
        receipts=receipts     # list of Receipt objects
    )


@bp.route("/expenses/report")
@login_required
def expense_report():
    q = (db.session.query(
             Receipt.category,
             db.func.sum(Receipt.gtq_amount).label("total_gtq"),
             db.func.sum(Receipt.usd_amount).label("total_usd"))
         .group_by(Receipt.category)
         .all())
    labels  = [row.category for row in q]
    totals  = [float(row.total_gtq) for row in q]

    return render_template("finance/report.html",
                           labels=json.dumps(labels),
                           totals=json.dumps(totals))




@bp.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    # Serve uploaded expense files
    return send_from_directory(Expense_Folder, filename)

@bp.route('/donations', methods=['GET', 'POST'])
@login_required
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

        # Process uploaded donations file
        df = load_and_clean(filepath)
        metrics = compute_metrics(df)

        # Generate chart of monthly donations
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

    # GET
    return render_template('finance/upload.html', title=_('Upload a file'))

@bp.route("/reports", methods=["GET"])
@login_required
def reports():
    # Placeholder; you can extend this as needed
    return "This is a crappy report"
