import pandas as pd
import numpy as np
import json
import re
from collections import Counter

# --- Configuration (should largely match eda.py for consistency) ---
DATA_FILE = "March to May 25 Purchases.csv"
RULES_OUTPUT_FILE = "procurement_rules.json"

# Columns - adjust if your CSV has different headers (should match eda.py)
DATE_COLUMN = 'Date'
ITEM_COLUMN_CANDIDATES = ['Description', 'Item Name', 'RawMaterial']
SUPPLIER_COLUMN_CANDIDATES = ['Supplier', 'Supplier Name', 'Vendor']
QUANTITY_COLUMN_CANDIDATES = ['Quantity', 'Qty', 'Amount']
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

# Parameters for procurement logic
DEFAULT_LEAD_TIME_DAYS = 7 # Days
SAFETY_STOCK_DAYS = 14 # Days of average usage
ANALYSIS_PERIOD_DAYS = 90 # Assumed period for daily usage calculation

# --- Helper Functions (from eda.py or similar) ---
def parse_quantity(description):
    if pd.isna(description): return np.nan
    description_str = str(description).lower()
    match = re.search(r'(\d[\d,]*\.?\d*)\s*(sheet|sheets|pack|packs|unit|units|roll|rolls|m|box|each|x)?', description_str)
    if match:
        try: return float(match.group(1).replace(',', ''))
        except ValueError: return np.nan
    match_simple_num = re.match(r'(\d[\d,]*\.?\d*)', description_str)
    if match_simple_num:
        try: return float(match_simple_num.group(1).replace(',', ''))
        except ValueError: return np.nan
    return np.nan

def find_column(df, candidates):
    for col in candidates:
        if col in df.columns:
            print(f"Found column: '{col}' for {', '.join(candidates)}")
            return col
    print(f"Warning: None of the candidate columns ({', '.join(candidates)}) found.")
    return None

# --- Main Logic ---
def main():
    print(f"Starting script to generate '{RULES_OUTPUT_FILE}'...")

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

    # --- Initial Cleaning and Column Identification ---
    item_col = find_column(df, ITEM_COLUMN_CANDIDATES)
    supplier_col = find_column(df, SUPPLIER_COLUMN_CANDIDATES)
    qty_col_actual = find_column(df, QUANTITY_COLUMN_CANDIDATES)
    category_col = find_column(df, CATEGORY_COLUMN_CANDIDATES)
    date_col = DATE_COLUMN # Assuming 'Date' is the date column as per eda.py

    if not item_col or not date_col or date_col not in df.columns:
        print("Error: Essential columns (item description or date) not found. Cannot proceed.")
        return

    # Convert date column
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
    df = df.dropna(subset=[date_col]) # Remove rows where date conversion failed

    # Prepare quantity column (parse if necessary, like in eda.py)
    df['parsed_quantity'] = df[item_col].apply(parse_quantity)
    qty_to_use = 'parsed_quantity'
    if qty_col_actual:
        df[qty_col_actual] = pd.to_numeric(df[qty_col_actual], errors='coerce')
        df[qty_col_actual] = df[qty_col_actual].fillna(df['parsed_quantity'])
        qty_to_use = qty_col_actual
    else:
        print("Using 'parsed_quantity' as no dedicated quantity column was found/suitable.")
    
    df[qty_to_use] = pd.to_numeric(df[qty_to_use], errors='coerce')
    print(f"Using '{qty_to_use}' for quantity calculations.")


    # --- Filtering Overheads (mirroring eda.py) ---
    print("\n--- Filtering Overheads ---")
    df_procurement = df.copy()
    if category_col:
        df_procurement = df_procurement[~df_procurement[category_col].astype(str).str.lower().isin([cat.lower() for cat in OVERHEAD_CATEGORIES])]
    if item_col:
        keyword_pattern = '|'.join([re.escape(keyword.lower()) for keyword in OVERHEAD_ITEM_KEYWORDS])
        df_procurement = df_procurement[~df_procurement[item_col].astype(str).str.lower().str.contains(keyword_pattern, na=False)]
    
    print(f"Rows remaining after overhead filtering: {len(df_procurement)}")
    if df_procurement.empty:
        print("No procurement data left after filtering. Cannot generate rules.")
        return

    # --- Calculate Procurement Parameters ---
    procurement_rules = []
    
    # Get unique materials from the filtered data
    # Ensure item_col and qty_to_use are valid before groupby
    if item_col not in df_procurement.columns or qty_to_use not in df_procurement.columns:
        print(f"Error: Item column ('{item_col}') or Quantity column ('{qty_to_use}') not found in filtered DataFrame.")
        return

    # Drop rows where essential item name or quantity is NaN for calculations
    df_calc = df_procurement.dropna(subset=[item_col, qty_to_use])


    for material_name, group in df_calc.groupby(item_col):
        print(f"\nProcessing: {material_name}")

        total_quantity_ordered = group[qty_to_use].sum()
        avg_daily_usage = total_quantity_ordered / ANALYSIS_PERIOD_DAYS
        
        # If avg_daily_usage is 0 or NaN, some subsequent calculations might be problematic
        if pd.isna(avg_daily_usage) or avg_daily_usage == 0:
            print(f"Warning: Average daily usage for {material_name} is {avg_daily_usage}. Some rules may be zero or defaults.")
            # Set to a very small number to avoid division by zero if necessary, or handle as per policy
            # For now, we'll let it be, but this can lead to ROP = Safety Stock if lead time calc becomes 0
            avg_daily_usage = 0 if pd.isna(avg_daily_usage) else avg_daily_usage


        lead_time = DEFAULT_LEAD_TIME_DAYS # Placeholder
        safety_stock = avg_daily_usage * SAFETY_STOCK_DAYS
        
        reorder_point = (avg_daily_usage * lead_time) + safety_stock
        
        # Calculate average order quantity for this specific material
        avg_order_quantity = group[qty_to_use].mean()
        if pd.isna(avg_order_quantity): # Handle cases with no valid quantity data for mean
            avg_order_quantity = avg_daily_usage * (lead_time + (SAFETY_STOCK_DAYS / 2)) # Fallback, e.g. cover leadtime + half safety
            avg_order_quantity = max(1, round(avg_order_quantity)) # Ensure it's at least 1
            print(f"Warning: Could not calculate avg_order_quantity for {material_name}, using fallback: {avg_order_quantity}")


        # Determine primary supplier
        primary_supplier = "N/A"
        if supplier_col and supplier_col in group.columns:
            supplier_counts = group[supplier_col].value_counts()
            if not supplier_counts.empty:
                primary_supplier = supplier_counts.index[0]
        
        procurement_rules.append({
            'RawMaterial': material_name,
            'AverageDailyUsage': round(avg_daily_usage, 2),
            'LeadTimeDays': lead_time,
            'SafetyStock': round(safety_stock, 2),
            'ReorderPoint': round(reorder_point, 2),
            'StandardOrderQuantity': round(avg_order_quantity, 2),
            'PrimarySupplier': primary_supplier
        })
        print(f"  Avg Daily Usage: {avg_daily_usage:.2f}, ROP: {reorder_point:.2f}, Order Qty: {avg_order_quantity:.2f}, Supplier: {primary_supplier}")

    # --- Save Rules to JSON ---
    if procurement_rules:
        try:
            with open(RULES_OUTPUT_FILE, 'w') as f:
                json.dump(procurement_rules, f, indent=4)
            print(f"\nSuccessfully saved procurement rules to '{RULES_OUTPUT_FILE}'. Contains {len(procurement_rules)} items.")
        except Exception as e:
            print(f"Error saving rules to JSON: {e}")
    else:
        print("\nNo procurement rules were generated (likely no materials found after filtering).")

if __name__ == "__main__":
    main()
