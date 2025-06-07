import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
import os

# --- Configuration & Constants ---
DATA_FILE = "March to May 25 Purchases.csv" # Ensure this matches your uploaded file name
# Columns - adjust these if your CSV has different headers
DATE_COLUMN = 'Date'
ITEM_COLUMN_CANDIDATES = ['Description', 'Item Name', 'RawMaterial'] # Order of preference
SUPPLIER_COLUMN_CANDIDATES = ['Supplier', 'Supplier Name', 'Vendor']
QUANTITY_COLUMN_CANDIDATES = ['Quantity', 'Qty', 'Amount']
CATEGORY_COLUMN_CANDIDATES = ['Material Type', 'Category', 'Type']

# Overhead filtering based on category
OVERHEAD_CATEGORIES = [
    'Shipping', 'Salaries', 'Rent', 'General', 'Admin', 'Software',
    'Utilities', 'Bank Charges', 'Consultancy', 'Travel', 'Marketing',
    'Taxes', 'Insurance', 'Maintenance', 'Staff Costs', 'Office Supplies', # Added Office Supplies
    'Logistics', 'IT Support', 'Legal Fees', 'Accounting Fees', 'Subscriptions', 'Training'
]
# Additional overhead filtering based on keywords in item description
OVERHEAD_ITEM_KEYWORDS = [
    'shipment', 'delivery', 'courier', 'consulting', 'fee', 'tax', 'vat',
    'service charge', 'bank charges', 'rent', 'salary', 'salaries', 'payroll',
    'interest', 'insurance', 'travel expenses', 'subscription', 'software license',
    'utilities', 'phone bill', 'internet bill', 'office cleaning', 'repairs'
]

TOP_N_PRODUCTS = 10
TOP_N_SUPPLIER_ITEMS = 3 # For analyzing top suppliers for specific items

# --- Helper Functions ---
def parse_quantity(description):
    """
    Attempts to parse a numerical quantity from a string.
    Handles formats like "1 sheet", "2 packs", "1,000 units".
    More sophisticated parsing might be needed for very complex cases.
    """
    if pd.isna(description):
        return np.nan

    # Convert to string in case it's a number already
    description_str = str(description).lower()

    # Try to find numbers followed by common units or just numbers
    # Looks for integers or decimals
    match = re.search(r'(\d[\d,]*\.?\d*)\s*(sheet|sheets|pack|packs|unit|units|roll|rolls|m|box|each|x)?', description_str)
    if match:
        try:
            quantity_str = match.group(1).replace(',', '') # Remove commas for float conversion
            return float(quantity_str)
        except ValueError:
            return np.nan # Could not convert

    # If no unit found, try to extract any number at the beginning
    match_simple_num = re.match(r'(\d[\d,]*\.?\d*)', description_str)
    if match_simple_num:
        try:
            quantity_str = match_simple_num.group(1).replace(',', '')
            return float(quantity_str)
        except ValueError:
            return np.nan
    return np.nan

def find_column(df, candidates):
    """Finds the first existing column from a list of candidates."""
    for col in candidates:
        if col in df.columns:
            print(f"Found column: '{col}' for {', '.join(candidates)}")
            return col
    print(f"Warning: None of the candidate columns ({', '.join(candidates)}) found.")
    return None

# --- Analysis Functions ---
def analyze_top_products(df, item_col, qty_col):
    print("\n--- Top Products Analysis ---")
    if item_col is None or qty_col is None or item_col not in df or qty_col not in df:
        print("Error: Item or Quantity column not found for top products analysis.")
        return

    # Ensure quantity is numeric and drop NaNs for this analysis
    df_analysis = df.copy()
    df_analysis[qty_col] = pd.to_numeric(df_analysis[qty_col], errors='coerce')
    df_analysis = df_analysis.dropna(subset=[item_col, qty_col])

    if df_analysis.empty:
        print("No data available for top products analysis after cleaning.")
        return

    # Group by item and sum quantities
    top_items = df_analysis.groupby(item_col)[qty_col].sum().nlargest(TOP_N_PRODUCTS)

    if top_items.empty:
        print("No top products found.")
        return

    print(f"Top {TOP_N_PRODUCTS} products by total quantity ordered:")
    print(top_items)

    plt.figure(figsize=(12, 7))
    top_items.sort_values(ascending=False).plot(kind='bar')
    plt.title(f'Top {TOP_N_PRODUCTS} Raw Materials/Items by Quantity Ordered')
    plt.xlabel('Raw Material/Item')
    plt.ylabel('Total Quantity Ordered')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    try:
        plt.savefig("top_products.png")
        print("Saved plot to top_products.png")
    except Exception as e:
        print(f"Error saving top_products.png: {e}")
    plt.show()


def analyze_supplier_usage(df, item_col, supplier_col, top_n_items_for_supplier_analysis=TOP_N_SUPPLIER_ITEMS):
    print("\n--- Supplier Analysis ---")
    if supplier_col is None or supplier_col not in df:
        print("Error: Supplier column not found for supplier analysis.")
        return
    if item_col is None or item_col not in df : # item_col needed for top item supplier analysis
        print("Error: Item column not found for supplier analysis (for top items).")
        # We can still do overall supplier frequency
        # return # Uncomment if you want to halt if item_col is missing

    df_analysis = df.copy().dropna(subset=[supplier_col])
    if df_analysis.empty:
        print("No data available for supplier analysis after cleaning.")
        return

    # Overall supplier frequency
    supplier_counts = df_analysis[supplier_col].value_counts()
    print("Overall supplier usage (by number of orders):")
    print(supplier_counts.head(TOP_N_PRODUCTS)) # Show top N suppliers

    plt.figure(figsize=(12, 7))
    supplier_counts.head(TOP_N_PRODUCTS).plot(kind='bar')
    plt.title(f'Top {TOP_N_PRODUCTS} Suppliers by Number of Orders')
    plt.xlabel('Supplier')
    plt.ylabel('Number of Orders')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    try:
        plt.savefig("supplier_frequency.png")
        print("Saved plot to supplier_frequency.png")
    except Exception as e:
        print(f"Error saving supplier_frequency.png: {e}")
    plt.show()

    # Primary suppliers for top N items (if item_col is available)
    if item_col and item_col in df_analysis:
        # First, find the actual top N items by order frequency or quantity. Let's use frequency for simplicity here.
        # This requires qty_col to be identified and numeric if using quantity.
        # For now, let's use order frequency of items.
        top_item_names = df_analysis[item_col].value_counts().nlargest(top_n_items_for_supplier_analysis).index.tolist()

        if not top_item_names:
            print("Could not determine top items for supplier breakdown.")
            return

        print(f"\nPrimary supplier analysis for top {top_n_items_for_supplier_analysis} most frequently ordered items:")
        for item_name in top_item_names:
            item_supplier_df = df_analysis[df_analysis[item_col] == item_name]
            if not item_supplier_df.empty:
                primary_suppliers = item_supplier_df[supplier_col].value_counts()
                print(f"\nItem: {item_name}")
                print(primary_suppliers)
            else:
                print(f"\nItem: {item_name} - No supplier data found after filtering.")
    else:
        print("\nSkipping primary supplier analysis for top items as item column was not identified.")


def analyze_order_cadence(df, item_col, date_col):
    print("\n--- Order Cadence Analysis ---")
    if item_col is None or date_col is None or item_col not in df or date_col not in df:
        print("Error: Item or Date column not found for order cadence analysis.")
        return

    df_analysis = df.copy()
    df_analysis = df_analysis.dropna(subset=[item_col, date_col])
    # Ensure date_col is datetime
    df_analysis[date_col] = pd.to_datetime(df_analysis[date_col], errors='coerce', dayfirst=True) # Assuming dayfirst, adjust if not
    df_analysis = df_analysis.dropna(subset=[date_col])


    if df_analysis.empty:
        print("No data available for order cadence analysis after cleaning.")
        return

    unique_items = df_analysis[item_col].unique()
    cadence_data = []

    for item in unique_items:
        item_orders = df_analysis[df_analysis[item_col] == item].sort_values(by=date_col)
        if len(item_orders) > 1:
            time_diffs = item_orders[date_col].diff().dt.days.dropna()
            if not time_diffs.empty:
                avg_cadence = time_diffs.mean()
                cadence_data.append({'Raw Material': item, 'Average Days Between Orders': avg_cadence})
            else:
                cadence_data.append({'Raw Material': item, 'Average Days Between Orders': 'N/A (only one order with valid date diff)'})
        else:
            cadence_data.append({'Raw Material': item, 'Average Days Between Orders': 'Single Order or Insufficient Data'})

    if cadence_data:
        cadence_df = pd.DataFrame(cadence_data)
        print(cadence_df)
    else:
        print("No items found for cadence analysis.")


def analyze_order_quantity(df, item_col, qty_col):
    print("\n--- Order Quantity Analysis ---")
    if item_col is None or qty_col is None or item_col not in df or qty_col not in df:
        print("Error: Item or Quantity column not found for order quantity analysis.")
        return

    df_analysis = df.copy()
    df_analysis[qty_col] = pd.to_numeric(df_analysis[qty_col], errors='coerce')
    df_analysis = df_analysis.dropna(subset=[item_col, qty_col])


    if df_analysis.empty:
        print("No data available for order quantity analysis after cleaning.")
        return

    quantity_stats = df_analysis.groupby(item_col)[qty_col].agg(['mean', 'median'])
    quantity_stats.columns = ['Average Quantity', 'Median Quantity']

    if quantity_stats.empty:
        print("No items found for quantity analysis.")
        return

    print(quantity_stats)

# --- Main Execution ---
def main():
    print("Starting EDA Script...")
    # Check if setup.py needs to be run (e.g., if requirements.txt is missing)
    if not os.path.exists("requirements.txt"):
        print("requirements.txt not found. Attempting to run setup.py...")
        try:
            import subprocess
            subprocess.run(['python', 'setup.py'], check=True)
            print("setup.py executed. Please ensure dependencies are installed before re-running eda.py if needed.")
        except Exception as e:
            print(f"Could not run setup.py: {e}. Please run it manually.")
            # Depending on policy, you might want to exit here
            # return

    # Load data
    try:
        df = pd.read_csv(DATA_FILE)
        print(f"Successfully loaded '{DATA_FILE}'.")
    except FileNotFoundError:
        print(f"Error: The file '{DATA_FILE}' was not found. Please ensure it's in the same directory as the script.")
        return
    except Exception as e:
        print(f"Error loading '{DATA_FILE}': {e}")
        return

    print("\n--- Initial Data Overview ---")
    print("First 5 rows of the dataset:")
    print(df.head())
    print("\nDataFrame Info:")
    df.info()
    print("\nMissing values summary:")
    print(df.isnull().sum())

    # --- Data Cleaning and Preparation ---
    print("\n--- Data Cleaning and Preparation ---")

    # Convert date column
    if DATE_COLUMN in df.columns:
        print(f"Converting '{DATE_COLUMN}' to datetime...")
        df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors='coerce', dayfirst=True) # Assuming dayfirst, adjust if not
        # df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors='coerce', format='%d/%m/%Y') # More specific format
    else:
        print(f"Warning: Date column '{DATE_COLUMN}' not found.")
        # Attempt to find a date column if DATE_COLUMN is not present
        # This is a basic example; more robust detection might be needed
        for col in df.columns:
            if 'date' in col.lower():
                print(f"Attempting to use column '{col}' as date column.")
                df[DATE_COLUMN] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
                break
        if DATE_COLUMN not in df.columns or df[DATE_COLUMN].isnull().all(): # Check if conversion failed or column not found
            print(f"Error: Could not identify or convert a usable date column. Exiting.")
            return


    # Identify actual column names to use
    item_column_name = find_column(df, ITEM_COLUMN_CANDIDATES)
    supplier_column_name = find_column(df, SUPPLIER_COLUMN_CANDIDATES)
    quantity_column_name_actual = find_column(df, QUANTITY_COLUMN_CANDIDATES)
    category_column_name = find_column(df, CATEGORY_COLUMN_CANDIDATES)

    # Attempt to parse quantity from description if a dedicated quantity column is problematic or missing
    # Create a working quantity column
    df['parsed_quantity'] = np.nan # Initialize

    if item_column_name: # We need an item description to parse from
        print(f"Attempting to parse quantity from '{item_column_name}' as 'parsed_quantity'.")
        df['parsed_quantity'] = df[item_column_name].apply(parse_quantity)

    # If a dedicated quantity column exists and is mostly good, use it. Otherwise, rely on parsed.
    # This logic can be refined. For now, if 'Quantity' exists, we assume it's the primary one,
    # but we'll fill its NaNs with parsed_quantity if possible.
    if quantity_column_name_actual:
        print(f"Using '{quantity_column_name_actual}' as primary quantity column.")
        df[quantity_column_name_actual] = pd.to_numeric(df[quantity_column_name_actual], errors='coerce')
        df[quantity_column_name_actual] = df[quantity_column_name_actual].fillna(df['parsed_quantity'])
        qty_col_to_use = quantity_column_name_actual
    else:
        print("Using 'parsed_quantity' as the primary quantity column as no dedicated one was found or suitable.")
        qty_col_to_use = 'parsed_quantity'

    print(f"Final quantity column to be used for analysis: '{qty_col_to_use}'")
    print(df[[item_column_name, qty_col_to_use]].head())


    # --- Filtering Overheads ---
    print("\n--- Filtering Overheads ---")
    original_row_count = len(df)
    df_filtered = df.copy()

    # Filter by category
    if category_column_name and category_column_name in df_filtered.columns:
        print(f"Filtering based on '{category_column_name}'. Excluding categories: {', '.join(OVERHEAD_CATEGORIES)}")
        df_filtered = df_filtered[~df_filtered[category_column_name].astype(str).str.lower().isin([cat.lower() for cat in OVERHEAD_CATEGORIES])]
        print(f"Rows after category filtering: {len(df_filtered)}")
    else:
        print("Warning: Category column not found. Category-based overhead filtering skipped.")

    # Filter by item description keywords
    if item_column_name and item_column_name in df_filtered.columns:
        print(f"Filtering based on keywords in '{item_column_name}'. Excluding keywords: {', '.join(OVERHEAD_ITEM_KEYWORDS)}")
        keyword_pattern = '|'.join([re.escape(keyword.lower()) for keyword in OVERHEAD_ITEM_KEYWORDS])
        df_filtered = df_filtered[~df_filtered[item_column_name].astype(str).str.lower().str.contains(keyword_pattern, na=False)]
        print(f"Rows after item keyword filtering: {len(df_filtered)}")
    else:
        print("Warning: Item description column not found. Item keyword-based overhead filtering skipped.")

    rows_removed = original_row_count - len(df_filtered)
    print(f"Total rows removed as overhead: {rows_removed}")
    print(f"Rows remaining for procurement analysis: {len(df_filtered)}")

    if df_filtered.empty:
        print("Error: All data was filtered out as overhead or no data remaining. Cannot proceed with analysis.")
        return

    # --- Run Analyses ---
    if item_column_name and qty_col_to_use:
        analyze_top_products(df_filtered, item_column_name, qty_col_to_use)
    else:
        print("Skipping Top Products Analysis: Item or Quantity column not identified.")

    if supplier_column_name:
        analyze_supplier_usage(df_filtered, item_column_name, supplier_column_name) # item_column_name can be None here
    else:
        print("Skipping Supplier Analysis: Supplier column not identified.")

    if item_column_name and DATE_COLUMN in df_filtered.columns:
        analyze_order_cadence(df_filtered, item_column_name, DATE_COLUMN)
    else:
        print("Skipping Order Cadence Analysis: Item or Date column not identified/valid.")

    if item_column_name and qty_col_to_use:
        analyze_order_quantity(df_filtered, item_column_name, qty_col_to_use)
    else:
        print("Skipping Order Quantity Analysis: Item or Quantity column not identified.")

    print("\nEDA Script finished.")

if __name__ == "__main__":
    main()
