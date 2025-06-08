import pandas as pd
import json
# Updated import from action.py
from action import generate_po_email_content, send_po_email 

# --- File Names ---
RULES_FILE = "procurement_rules.json"
SUPPLIERS_FILE = "suppliers.json"
INVENTORY_FILE = "current_inventory.csv"

def load_json_file(file_path):
    """Loads a JSON file and returns its content."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        print(f"Successfully loaded {file_path}")
        return data
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{file_path}'. Make sure it's valid JSON.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading '{file_path}': {e}")
        return None

def load_csv_file(file_path):
    """Loads a CSV file into a pandas DataFrame."""
    try:
        df = pd.read_csv(file_path)
        print(f"Successfully loaded {file_path}")
        return df
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading '{file_path}': {e}")
        return None

def main():
    print("--- Starting Procurement Agent ---")

    # Load all necessary data files
    procurement_rules = load_json_file(RULES_FILE)
    supplier_contacts = load_json_file(SUPPLIERS_FILE)
    inventory_df = load_csv_file(INVENTORY_FILE)

    if not procurement_rules or not supplier_contacts or inventory_df is None:
        print("Error: One or more essential data files could not be loaded. Exiting.")
        return

    rules_map = {rule['RawMaterial']: rule for rule in procurement_rules}
    items_to_order_by_supplier = {}

    print("\n--- Checking Inventory Levels ---")
    for index, row in inventory_df.iterrows():
        material = row['RawMaterial']
        current_stock = row['CurrentStock']

        if material not in rules_map:
            print(f"Warning: No procurement rules found for '{material}'. Skipping.")
            continue

        rule = rules_map[material]
        reorder_point = rule.get('ReorderPoint', float('inf'))

        print(f"Checking: {material} (Stock: {current_stock}, ROP: {reorder_point})")

        if current_stock < reorder_point:
            print(f"  Action: Reorder needed for {material}.")
            primary_supplier_name = rule.get('PrimarySupplier')
            order_quantity = rule.get('StandardOrderQuantity')

            if not primary_supplier_name or primary_supplier_name == "N/A":
                print(f"  Warning: No primary supplier defined for '{material}'. Cannot generate PO.")
                continue
            
            if order_quantity is None or order_quantity <= 0:
                print(f"  Warning: Invalid or zero order quantity for '{material}' (Qty: {order_quantity}). Cannot generate PO.")
                continue

            if primary_supplier_name not in items_to_order_by_supplier:
                items_to_order_by_supplier[primary_supplier_name] = []
            
            items_to_order_by_supplier[primary_supplier_name].append({
                'name': material,
                'quantity': order_quantity
            })
            print(f"  Added {material} (Qty: {order_quantity}) to order list for supplier {primary_supplier_name}")
        else:
            print(f"  OK: Stock for {material} is sufficient.")

    if not items_to_order_by_supplier:
        print("\n--- No items require reordering at this time. ---")
    else:
        print("\n--- Processing Orders and Sending Emails ---")
        for supplier_name, items in items_to_order_by_supplier.items():
            print(f"\n--- PROCESSING ORDER FOR SUPPLIER: {supplier_name.upper()} ---")
            
            supplier_info = supplier_contacts.get(supplier_name)
            if not supplier_info or not supplier_info.get('email'):
                print(f"  Warning: Email address not found for supplier '{supplier_name}' in {SUPPLIERS_FILE}. Cannot send email.")
                continue
            
            supplier_email = supplier_info['email']
            if not supplier_email: # Handles case where email key exists but value is null/empty
                 print(f"  Warning: Email address is blank for supplier '{supplier_name}' in {SUPPLIERS_FILE}. Cannot send email.")
                 continue

            print(f"  Preparing PO for {supplier_name} ({supplier_email}) for {len(items)} item(s).")
            subject, body = generate_po_email_content(supplier_name, items)
            
            if subject and body:
                print(f"  Attempting to send email to {supplier_email}...")
                # Ensure your action.py's SMTP settings are configured via environment variables for security
                success = send_po_email(supplier_email, subject, body)
                if success:
                    print(f"  Successfully sent PO email to {supplier_name} at {supplier_email}.")
                else:
                    print(f"  Failed to send PO email to {supplier_name}. Check action.py logs/SMTP settings in environment variables.")
            else:
                # This case should ideally not be reached if items list is valid
                print(f"  Error: Could not generate email content for {supplier_name}. Items: {items}")
            print(f"--- FINISHED PROCESSING SUPPLIER: {supplier_name.upper()} ---")

    print("\n--- Procurement Agent Finished ---")

if __name__ == "__main__":
    main()
