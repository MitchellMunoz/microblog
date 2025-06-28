import pandas as pd
import matplotlib.pyplot as plt

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename: str) -> bool:
    """
    Check if the filename has an allowed extension.
    """
    return (
        '.' in filename and 
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def load_and_clean(csv_path: str) -> pd.DataFrame:
    """
    Load a donations CSV, clean up columns, and return a standardized DataFrame.
    """
    df = pd.read_csv(csv_path)
    df = df[[
        'donor_first_name', 'donor_last_name',
        'amount', 'received_date',
        'donor_email', 'donor_address'
    ]].copy()

    # Combine names and normalize amount
    df['donor_full_name'] = (
        df['donor_first_name'] + ' ' + df['donor_last_name']
    )
    df['amount'] = (
        df['amount']
          .replace('[/$,]', '', regex=True)
          .astype(float)
    )

    # Parse dates
    df['received_date'] = pd.to_datetime(df['received_date'])

    return df[[
        'donor_full_name', 'amount',
        'received_date', 'donor_email', 'donor_address'
    ]]


def compute_metrics(df: pd.DataFrame) -> dict:
    """
    Given a cleaned DataFrame, return key metrics:
      - top_donors: dict{name: total_amount}
      - average: float
      - monthly_totals: dict{period: total_amount}
      - repeat_donors: list of names who donated more than once
    """
    top = (
        df.groupby('donor_full_name')['amount']
          .sum()
          .nlargest(10)
          .to_dict()
    )
    avg = float(df['amount'].mean())
    monthly = (
        df
          .groupby(df['received_date'].dt.to_period('M'))['amount']
          .sum()
          .astype(float)
          .to_dict()
    )
    freq = df['donor_full_name'].value_counts()
    repeaters = freq[freq > 1].index.tolist()

    return {
        'top_donors': top,
        'average': avg,
        'monthly_totals': monthly,
        'repeat_donors': repeaters
    }


def plot_monthly_totals(monthly_totals: dict, out_path: str) -> None:
    """
    Generate and save a bar chart of monthly totals to the given file path.
    """
    labels = [str(m) for m in monthly_totals.keys()]
    values = list(monthly_totals.values())

    plt.figure()
    plt.bar(labels, values)
    plt.xticks(rotation=45, ha='right')
    plt.title("Monthly Donations")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
