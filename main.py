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
                         'OrderMethod', 'Status', 'QuantityReceived', 'DateReceived', 'Notes']

def load_csv_to_dataframe(file_path, expected_headers, create_if_missing=False):
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            df = pd.read_csv(file_path, dtype=str).fillna('')
            current_headers = df.columns.tolist()

            if file_path == ORDER_HISTORY_FILE:
                if 'QuantityReceived' not in current_headers:
                    df['QuantityReceived'] = '0'
                else:
                    df['QuantityReceived'] = df['QuantityReceived'].replace('', '0').fillna('0')

                if 'DateReceived' not in current_headers:
                    df['DateReceived'] = ''
                # else: # fillna('') already handled existing empty strings
                    # df['DateReceived'] = df['DateReceived'].fillna('')

            # Ensure all other expected columns are present
            for header in expected_headers:
                if header not in df.columns: # Check against df.columns as current_headers might not be updated if columns were added above
                    df[header] = ''

            return df[expected_headers] # Return with expected order and all columns present
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

def main(logger_func=None):
    summary_report = []

    def log_message(message):
        if logger_func:
            logger_func(message)
        else:
            print(message)
        summary_report.append(str(message)) # Also add to summary report

    log_message("--- Starting Procurement Order Generation ---")
    materials_df = load_csv_to_dataframe(MATERIALS_MASTER_FILE, MATERIALS_HEADERS)
    suppliers_df = load_csv_to_dataframe(SUPPLIERS_FILE, SUPPLIERS_HEADERS)
    # Create order_history.csv with headers if it doesn't exist or is empty
    load_csv_to_dataframe(ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS, create_if_missing=True)

    if materials_df.empty:
        msg = f"Error: {MATERIALS_MASTER_FILE} empty. Exiting."
        log_message(msg)
        summary_report.append(msg)
        return summary_report
    
    items_to_order_by_supplier = {} 

    log_message("\n--- Checking Material Stock Levels ---")
    for _, mat_row in materials_df.iterrows():
        try:
            mat_id = str(mat_row.get('MaterialID', '')).strip()
            mat_name = str(mat_row.get('MaterialName', 'Unknown')).strip()
            stock = float(mat_row.get('CurrentStock', 0)); rop = float(mat_row.get('ReorderPoint', float('inf')))
            log_message(f"Checking: {mat_name} (ID: {mat_id}, Stock: {stock}, ROP: {rop})")
            if stock < rop:
                log_message(f"  Reorder needed for {mat_name}.")
                sup_id = str(mat_row.get('PreferredSupplierID', '')).strip()
                order_qty = float(mat_row.get('StandardOrderQuantity', 0))
                price = float(mat_row.get('CurrentPrice', 0))
                url = str(mat_row.get('ProductPageURL', '')).strip()
                if not sup_id or order_qty <= 0:
                    log_message(f"  Skipping: Missing SupplierID or invalid OrderQty for {mat_name}.")
                    continue
                items_to_order_by_supplier.setdefault(sup_id, []).append({
                    'MaterialID': mat_id, 'MaterialName': mat_name, 'QuantityOrdered': order_qty,
                    'UnitPricePaid': price, 'ProductPageURL': url })
                log_message(f"  Added {mat_name} (Qty: {order_qty}) for supplier ID {sup_id}")
        except ValueError as ve:
            log_message(f"  Skipping material {mat_row.get('MaterialID', 'Unknown')} due to data error: {ve}")
        except Exception as e:
            log_message(f"  Error with material {mat_row.get('MaterialID', 'Unknown')}: {e}")

    if not items_to_order_by_supplier:
        msg = "\n--- No items require reordering. ---"
        log_message(msg)
        summary_report.append(msg)
        return summary_report
    
    log_message("\n--- Processing Orders ---")
    for sup_id, items in items_to_order_by_supplier.items():
        sup_info_rows = suppliers_df[suppliers_df['SupplierID'] == sup_id]
        if sup_info_rows.empty:
            msg = f"Warning: SupplierID '{sup_id}' not found. Cannot order: {[i['MaterialName'] for i in items]}."
            log_message(msg)
            summary_report.append(msg)
            continue
        
        sup_info = sup_info_rows.iloc[0]
        sup_name = str(sup_info.get('SupplierName', sup_id)); method = str(sup_info.get('OrderMethod', '')).lower().strip()
        email_address = str(sup_info.get('Email', '')).strip(); web = str(sup_info.get('Website', '')).strip()
        
        log_message(f"\n--- ORDER FOR SUPPLIER: {sup_name} (ID: {sup_id}) ---")
        order_id = generate_order_id(); timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history_entries = []
        email_items_list = [{'name': i['MaterialName'], 'quantity': i['QuantityOrdered']} for i in items]
        logged_method = ""

        if method == "email":
            if not email_address:
                logged_method = "failed_email_no_address"
                log_message(f"  Error: No email for {sup_name}.")
            else:
                log_message(f"  Preparing email for {len(email_items_list)} item(s) to {email_address}...")
                subj, body = generate_po_email_content(sup_name, email_items_list)
                if subj and body:
                    log_message(f"  Attempting to send email...")
                    # Assuming send_po_email is robust and returns True/False
                    # success = send_po_email(email_address, subj, body)
                    success = False # Placeholder for now as send_po_email might have side effects or require setup
                    log_message(f"  Email sending function called. Placeholder success: {success}")
                    logged_method = "email_sent" if success else "email_failed_send_placeholder" # Updated placeholder
                    # log_message(f"  Email to {sup_name} {'succeeded' if success else 'failed'}.") # Original
                else:
                    logged_method = "email_failed_content"
                    log_message(f"  Error generating email content for {sup_name}.")
        elif method == "online":
            logged_method = "online_prompted"
            log_message("  Action: Place ONLINE order with:")
            for i in items: log_message(f"    - {i['MaterialName']} (Qty: {i['QuantityOrdered']}) URL: {i['ProductPageURL'] if i['ProductPageURL'] else web}")
        elif method == "phone":
            logged_method = "phone_prompted"
            log_message(f"  Action: Place PHONE order with {sup_name} (Phone: {sup_info.get('Phone', 'N/A')}):")
            for i in items: log_message(f"    - {i['MaterialName']}: {i['QuantityOrdered']}")
        else:
            logged_method = f"manual_review_method_{method if method else 'unknown'}"
            log_message(f"  Warning: Unknown OrderMethod ('{method}') for {sup_name}. Items:")
            for i in items: log_message(f"    - {i['MaterialName']}: {i['QuantityOrdered']}")

        for i in items:
            history_entries.append({
                'OrderID': order_id, 'Timestamp': timestamp, 'MaterialID': i['MaterialID'], 
                'MaterialName': i['MaterialName'], 'QuantityOrdered': i['QuantityOrdered'],
                'UnitPricePaid': i['UnitPricePaid'], 'TotalPricePaid': i['QuantityOrdered'] * i['UnitPricePaid'],
                'SupplierID': sup_id, 'SupplierName': sup_name, 'OrderMethod': logged_method,
                'Status': 'Ordered', 'QuantityReceived': '0', 'DateReceived': '', 'Notes': '' }) # Ensure QuantityReceived is string for consistency
        
        if history_entries:
            append_to_csv(pd.DataFrame(history_entries), ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS)
            log_message(f"  Logged {len(history_entries)} item(s) to {ORDER_HISTORY_FILE} with OrderID {order_id}")
        log_message(f"--- FINISHED SUPPLIER: {sup_name.upper()} ---")
    log_message("\n--- Procurement Order Generation Finished ---")
    return summary_report

if __name__ == "__main__": main()
