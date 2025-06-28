from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from werkzeug.utils import secure_filename
from flask_babel import _
import os
from flask_login import login_required
from app.finance import bp
from app.finance.config import Donations_Folder, Expense_Folder
from app.finance.utils import load_and_clean, compute_metrics, plot_monthly_totals

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
    # initialize filename and receipts list
    filename = None
    receipts = []
    if os.path.isdir(Expense_Folder):
        receipts = sorted(os.listdir(Expense_Folder))

    if request.method == 'POST':
        # Check that the file part exists
        file = request.files.get('file')
        if not file:
            flash(_('No file part in the request.'))
            return redirect(request.url)

        if file.filename == '':
            flash(_('No file selected.'))
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash(_('Invalid file type.'))
            return redirect(request.url)

        # ensure the folder exists and save file
        os.makedirs(Expense_Folder, exist_ok=True)
        filename = secure_filename(file.filename)
        filepath = os.path.join(Expense_Folder, filename)
        file.save(filepath)

        flash(_('Receipt "%(name)s" uploaded successfully.', name=filename))
        return redirect(url_for('finance.receipts'))

    # GET: show upload form and list existing receipts
    return render_template(
        'finance/expenses.html',
        filename=filename,
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
        # Check that the file part exists
        file = request.files.get('file')
        if not file:
            flash(_('No file part in the request.'))
            return redirect(request.url)

        # Check that a filename was provided
        filename = secure_filename(file.filename)
        if file.filename == '':
            flash(_('No file selected.'))
            return redirect(request.url)

        # Validate extension
        if not allowed_file(file.filename):
            flash(_('Invalid file type.'))
            return redirect(request.url)

        # ensure the folder exists and save file
        os.makedirs(Donations_Folder, exist_ok=True)
        filepath = os.path.join(Donations_Folder, filename)
        file.save(filepath)

        # Process the file with pandas helpers
        df = load_and_clean(filepath)
        metrics = compute_metrics(df)

        # Optionally generate and save a chart
        chart_name = f"{os.path.splitext(filename)[0]}_monthly.png"
        chart_dir = os.path.join(current_app.static_folder, 'charts')
        os.makedirs(chart_dir, exist_ok=True)
        chart_path = os.path.join(chart_dir, chart_name)
        plot_monthly_totals(metrics['monthly_totals'], chart_path)
        chart_url = url_for('static', filename=f'charts/{chart_name}')

        # Render the results
        return render_template(
            'finance/report.html',
            filename=filename,
            chart_url=chart_url,
            **metrics
        )

    # GET: show upload form
    return render_template('finance/upload.html', title=_('Upload a file'))
