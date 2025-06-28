import os

# path to the finance blueprint’s package folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# uploads subfolder inside app/finance/uploads
Donations_Folder = os.path.join(BASE_DIR, 'donations')

Expense_Folder = os.path.join(BASE_DIR, 'expenses')
