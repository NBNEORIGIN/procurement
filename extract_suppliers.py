import pandas as pd
import re

# --- Configuration (should match eda.py for consistency) ---
DATA_FILE = "March to May 25 Purchases.csv"

# Columns
SUPPLIER_COLUMN_CANDIDATES = ['Supplier', 'Supplier Name', 'Vendor']
ITEM_COLUMN_CANDIDATES = ['Description', 'Item Name', 'RawMaterial'] # For filtering
CATEGORY_COLUMN_CANDIDATES = ['Material Type', 'Category', 'Type'] # For filtering

# Overhead filtering (should match eda.py and logic.py)
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
    for col in candidates:
        if col in df.columns:
            # print(f"Found column: '{col}' for {', '.join(candidates)}")
            return col
    # print(f"Warning: None of the candidate columns ({', '.join(candidates)}) found.")
    return None

def main():
    print(f"Starting script to extract unique supplier names from '{DATA_FILE}'...")

    try:
        df = pd.read_csv(DATA_FILE)
        # print(f"Successfully loaded '{DATA_FILE}'.")
    except FileNotFoundError:
        print(f"Error: The file '{DATA_FILE}' was not found.")
        return
    except Exception as e:
        print(f"Error loading '{DATA_FILE}': {e}")
        return

    supplier_col = find_column(df, SUPPLIER_COLUMN_CANDIDATES)
    item_col = find_column(df, ITEM_COLUMN_CANDIDATES) # Needed for filtering context
    category_col = find_column(df, CATEGORY_COLUMN_CANDIDATES) # Needed for filtering context


    if not supplier_col:
        print("Error: Supplier column not found. Cannot extract supplier names.")
        return

    # --- Filtering Overheads (to get suppliers of procurement items primarily) ---
    # You might decide to remove this filtering if you want ALL suppliers, including overhead ones.
    df_filtered = df.copy()
    if category_col:
        df_filtered = df_filtered[~df_filtered[category_col].astype(str).str.lower().isin([cat.lower() for cat in OVERHEAD_CATEGORIES])]
    if item_col: # Ensure item_col exists before trying to use it for keyword filtering
        keyword_pattern = '|'.join([re.escape(keyword.lower()) for keyword in OVERHEAD_ITEM_KEYWORDS])
        df_filtered = df_filtered[~df_filtered[item_col].astype(str).str.lower().str.contains(keyword_pattern, na=False)]
    
    print(f"Number of rows after attempting to filter overheads: {len(df_filtered)}")
    
    unique_suppliers = df_filtered[supplier_col].dropna().unique()
    unique_suppliers.sort() # Sort for consistent order

    if len(unique_suppliers) > 0:
        print("\n--- Unique Supplier Names ---")
        for s_name in unique_suppliers:
            print(s_name)
        print(f"\nFound {len(unique_suppliers)} unique supplier names after filtering.")
        print("Please provide the email address for each of these suppliers.")
    else:
        print("No unique supplier names found after filtering. Check your data or filtering logic.")

if __name__ == "__main__":
    main()
