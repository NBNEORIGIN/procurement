import pandas as pd
import re
import numpy as np # Required for np.nan if used in parse_quantity if you were to copy it

# --- Configuration (should match eda.py for consistency) ---
DATA_FILE = "March to May 25 Purchases.csv"
OUTPUT_INVENTORY_FILE = "current_inventory.csv"
DEFAULT_STOCK_LEVEL = 100

# Columns - adjust if your CSV has different headers (should match eda.py)
ITEM_COLUMN_CANDIDATES = ['Description', 'Item Name', 'RawMaterial']
CATEGORY_COLUMN_CANDIDATES = ['Material Type', 'Category', 'Type']

# Overhead filtering (should match eda.py)
OVERHEAD_CATEGORIES = [
    'Shipping', 'Salaries', 'Rent', 'General', 'Admin', 'Software',
    'Utilities', 'Bank Charges', 'Consultancy', 'Travel', 'Marketing',
    'Taxes', 'Insurance', 'Maintenance', 'Staff Costs', 'Office Supplies',
    'Logistics', 'IT Support', 'Legal Fees', 'Accounting Fees', 'Subscriptions', 'Training'
]
OVERHEAD_ITEM_KEYWORDS = [
    'shipment', 'delivery', 'courier', 'consulting', 'fee', 'tax', 'vat',
    'service charge', 'bank charges', 'rent', 'salary', 'salaries', 'payroll',
    'interest', 'insurance', 'travel expenses', 'subscription', 'software license',
    'utilities', 'phone bill', 'internet bill', 'office cleaning', 'repairs'
]

def find_column(df, candidates):
    """Finds the first existing column from a list of candidates."""
    for col in candidates:
        if col in df.columns:
            print(f"Found column: '{col}' for {', '.join(candidates)}")
            return col
    print(f"Warning: None of the candidate columns ({', '.join(candidates)}) found for filtering.")
    return None

def main():
    print(f"Starting script to create '{OUTPUT_INVENTORY_FILE}'...")

    # Load data
    try:
        df = pd.read_csv(DATA_FILE)
        print(f"Successfully loaded '{DATA_FILE}'.")
    except FileNotFoundError:
        print(f"Error: The file '{DATA_FILE}' was not found.")
        return
    except Exception as e:
        print(f"Error loading '{DATA_FILE}': {e}")
        return

    # Identify actual column names to use for filtering
    item_column_name = find_column(df, ITEM_COLUMN_CANDIDATES)
    category_column_name = find_column(df, CATEGORY_COLUMN_CANDIDATES)

    if not item_column_name:
        print("Error: Could not identify a suitable item description column. Cannot determine unique raw materials.")
        return

    # --- Filtering Overheads (mirroring eda.py) ---
    print("\n--- Filtering Overheads ---")
    original_row_count = len(df)
    df_filtered = df.copy()

    # Filter by category
    if category_column_name and category_column_name in df_filtered.columns:
        print(f"Filtering based on '{category_column_name}'. Excluding categories: {', '.join(OVERHEAD_CATEGORIES)}")
        df_filtered = df_filtered[~df_filtered[category_column_name].astype(str).str.lower().isin([cat.lower() for cat in OVERHEAD_CATEGORIES])]
    else:
        print("Warning: Category column not found. Category-based overhead filtering skipped.")

    # Filter by item description keywords
    if item_column_name and item_column_name in df_filtered.columns:
        print(f"Filtering based on keywords in '{item_column_name}'. Excluding keywords: {', '.join(OVERHEAD_ITEM_KEYWORDS)}")
        keyword_pattern = '|'.join([re.escape(keyword.lower()) for keyword in OVERHEAD_ITEM_KEYWORDS])
        df_filtered = df_filtered[~df_filtered[item_column_name].astype(str).str.lower().str.contains(keyword_pattern, na=False)]

    rows_removed = original_row_count - len(df_filtered)
    print(f"Total rows removed as overhead: {rows_removed}")
    print(f"Rows remaining for identifying raw materials: {len(df_filtered)}")

    if df_filtered.empty:
        print("Error: All data was filtered out as overhead. Cannot create inventory file.")
        return

    # Get unique raw materials from the identified item column
    unique_raw_materials = df_filtered[item_column_name].dropna().unique()

    if len(unique_raw_materials) == 0:
        print("No unique raw materials found after filtering. Inventory file will be empty.")
    else:
        print(f"Found {len(unique_raw_materials)} unique raw materials.")

    # Create the current_inventory DataFrame
    inventory_df = pd.DataFrame({
        'RawMaterial': unique_raw_materials,
        'CurrentStock': DEFAULT_STOCK_LEVEL
    })

    # Save to CSV
    try:
        inventory_df.to_csv(OUTPUT_INVENTORY_FILE, index=False)
        print(f"Successfully created '{OUTPUT_INVENTORY_FILE}' with {len(inventory_df)} items.")
    except Exception as e:
        print(f"Error saving '{OUTPUT_INVENTORY_FILE}': {e}")

if __name__ == "__main__":
    main()
