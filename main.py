import pandas as pd
from datetime import datetime
import os
from action import generate_po_email_content, send_po_email # Ensure action.py is ready

MATERIALS_MASTER_FILE = "materials_master.csv"
SUPPLIERS_FILE = "suppliers.csv"
ORDER_HISTORY_FILE = "order_history.csv"

MATERIALS_HEADERS = ['MaterialID', 'MaterialName', 'Category', 'UnitOfMeasure', 'CurrentStock', 
                     'ReorderPoint', 'StandardOrderQuantity', 'PreferredSupplierID', 
                     'ProductPageURL', 'LeadTimeDays', 'SafetyStockQuantity', 'Notes', 'CurrentPrice']
SUPPLIERS_HEADERS = ['SupplierID', 'SupplierName', 'ContactPerson', 'Email', 'Phone', 'Website', 'OrderMethod']
ORDER_HISTORY_HEADERS = ['OrderID', 'Timestamp', 'MaterialID', 'MaterialName', 'QuantityOrdered', 
                         'UnitPricePaid', 'TotalPricePaid', 'SupplierID', 'SupplierName', 
                         'OrderMethod', 'Status', 'Notes']

def load_csv_to_dataframe(file_path, expected_headers, create_if_missing=False):
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            df = pd.read_csv(file_path, dtype=str).fillna('')
            for header in expected_headers:
                if header not in df.columns: df[header] = ''
            return df[expected_headers] 
        except Exception as e:
            print(f"Error loading {file_path}: {e}. Returning empty DF.")
            return pd.DataFrame(columns=expected_headers)
    elif create_if_missing:
        df = pd.DataFrame(columns=expected_headers); df.to_csv(file_path, index=False)
        return df
    return pd.DataFrame(columns=expected_headers)

def append_to_csv(df_to_append, file_path, expected_headers):
    # Ensure the DataFrame to append has all expected columns in the correct order
    df_ready_to_append = pd.DataFrame(columns=expected_headers)
    for col in expected_headers:
        if col in df_to_append.columns:
            df_ready_to_append[col] = df_to_append[col]
        else:
            df_ready_to_append[col] = None # Or appropriate default like ""
    
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        df_ready_to_append.to_csv(file_path, index=False, header=True)
    else:
        df_ready_to_append.to_csv(file_path, index=False, header=False, mode='a')

def generate_order_id():
    return f"PO-{datetime.now().strftime('%Y%m%d-%H%M%S%f')[:-3]}"

def main():
    print("--- Starting Procurement Order Generation ---")
    materials_df = load_csv_to_dataframe(MATERIALS_MASTER_FILE, MATERIALS_HEADERS)
    suppliers_df = load_csv_to_dataframe(SUPPLIERS_FILE, SUPPLIERS_HEADERS)
    # Create order_history.csv with headers if it doesn't exist or is empty
    load_csv_to_dataframe(ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS, create_if_missing=True)


    if materials_df.empty: print(f"Error: {MATERIALS_MASTER_FILE} empty. Exiting."); return
    
    items_to_order_by_supplier = {} 

    print("\n--- Checking Material Stock Levels ---")
    for _, mat_row in materials_df.iterrows():
        try:
            mat_id = str(mat_row.get('MaterialID', '')).strip()
            mat_name = str(mat_row.get('MaterialName', 'Unknown')).strip()
            stock = float(mat_row.get('CurrentStock', 0)); rop = float(mat_row.get('ReorderPoint', float('inf')))
            print(f"Checking: {mat_name} (ID: {mat_id}, Stock: {stock}, ROP: {rop})")
            if stock < rop:
                print(f"  Reorder needed for {mat_name}.")
                sup_id = str(mat_row.get('PreferredSupplierID', '')).strip()
                order_qty = float(mat_row.get('StandardOrderQuantity', 0))
                price = float(mat_row.get('CurrentPrice', 0))
                url = str(mat_row.get('ProductPageURL', '')).strip()
                if not sup_id or order_qty <= 0: print(f"  Skipping: Missing SupplierID or invalid OrderQty for {mat_name}."); continue
                items_to_order_by_supplier.setdefault(sup_id, []).append({
                    'MaterialID': mat_id, 'MaterialName': mat_name, 'QuantityOrdered': order_qty,
                    'UnitPricePaid': price, 'ProductPageURL': url })
                print(f"  Added {mat_name} (Qty: {order_qty}) for supplier ID {sup_id}")
        except ValueError as ve: print(f"  Skipping material {mat_row.get('MaterialID', 'Unknown')} due to data error: {ve}")
        except Exception as e: print(f"  Error with material {mat_row.get('MaterialID', 'Unknown')}: {e}")

    if not items_to_order_by_supplier: print("\n--- No items require reordering. ---"); return
    
    print("\n--- Processing Orders ---")
    for sup_id, items in items_to_order_by_supplier.items():
        sup_info_rows = suppliers_df[suppliers_df['SupplierID'] == sup_id]
        if sup_info_rows.empty: print(f"Warning: SupplierID '{sup_id}' not found. Cannot order: {[i['MaterialName'] for i in items]}."); continue
        
        sup_info = sup_info_rows.iloc[0]
        sup_name = str(sup_info.get('SupplierName', sup_id)); method = str(sup_info.get('OrderMethod', '')).lower().strip()
        email = str(sup_info.get('Email', '')).strip(); web = str(sup_info.get('Website', '')).strip()
        
        print(f"\n--- ORDER FOR SUPPLIER: {sup_name} (ID: {sup_id}) ---")
        order_id = generate_order_id(); timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history_entries = []
        email_items = [{'name': i['MaterialName'], 'quantity': i['QuantityOrdered']} for i in items]
        logged_method = ""

        if method == "email":
            if not email: logged_method = "failed_email_no_address"; print(f"  Error: No email for {sup_name}.")
            else:
                print(f"  Preparing email for {len(email_items)} item(s) to {email}...")
                subj, body = generate_po_email_content(sup_name, email_items)
                if subj and body:
                    print(f"  Attempting to send email...")
                    success = send_po_email(email, subj, body)
                    logged_method = "email_sent" if success else "email_failed_send"
                    print(f"  Email to {sup_name} {'succeeded' if success else 'failed'}.")
                else: logged_method = "email_failed_content"; print(f"  Error generating email content for {sup_name}.")
        elif method == "online":
            logged_method = "online_prompted"; print("  Action: Place ONLINE order with:")
            for i in items: print(f"    - {i['MaterialName']} (Qty: {i['QuantityOrdered']}) URL: {i['ProductPageURL'] if i['ProductPageURL'] else web}")
        elif method == "phone":
            logged_method = "phone_prompted"; print(f"  Action: Place PHONE order with {sup_name} (Phone: {sup_info.get('Phone', 'N/A')}):")
            for i in items: print(f"    - {i['MaterialName']}: {i['QuantityOrdered']}")
        else:
            logged_method = f"manual_review_method_{method if method else 'unknown'}"
            print(f"  Warning: Unknown OrderMethod ('{method}') for {sup_name}. Items:")
            for i in items: print(f"    - {i['MaterialName']}: {i['QuantityOrdered']}")

        for i in items:
            history_entries.append({
                'OrderID': order_id, 'Timestamp': timestamp, 'MaterialID': i['MaterialID'], 
                'MaterialName': i['MaterialName'], 'QuantityOrdered': i['QuantityOrdered'],
                'UnitPricePaid': i['UnitPricePaid'], 'TotalPricePaid': i['QuantityOrdered'] * i['UnitPricePaid'],
                'SupplierID': sup_id, 'SupplierName': sup_name, 'OrderMethod': logged_method,
                'Status': 'Ordered', 'Notes': '' })
        
        if history_entries:
            append_to_csv(pd.DataFrame(history_entries), ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS)
            print(f"  Logged {len(history_entries)} item(s) to {ORDER_HISTORY_FILE} with OrderID {order_id}")
        print(f"--- FINISHED SUPPLIER: {sup_name.upper()} ---")
    print("\n--- Procurement Order Generation Finished ---")

if __name__ == "__main__": main()
