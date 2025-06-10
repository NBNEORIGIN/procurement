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
    # This function now primarily identifies suggested orders.
    # The actual processing is moved to process_single_purchase_order and log_order_to_history

    _summary_report_for_logging_only = [] # Internal logging for this function's execution
    def log_message(message):
        if logger_func:
            logger_func(message)
        else:
            print(message)
        _summary_report_for_logging_only.append(str(message))

    log_message("--- Identifying Suggested Orders ---")
    materials_df = load_csv_to_dataframe(MATERIALS_MASTER_FILE, MATERIALS_HEADERS)
    # suppliers_df is loaded by the caller (GUI) if needed for process_single_purchase_order

    # Ensure order_history.csv exists with headers, create if not.
    # This is important because process_single_purchase_order will append to it.
    load_csv_to_dataframe(ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS, create_if_missing=True)

    if materials_df.empty:
        msg = f"Error: {MATERIALS_MASTER_FILE} is empty or not found. Cannot generate suggestions."
        log_message(msg)
        return [], _summary_report_for_logging_only # Return empty list of suggestions

    suggested_orders_list = []
    log_message("\n--- Checking Material Stock Levels for Suggestions ---")
    for _, mat_row in materials_df.iterrows():
        try:
            mat_id = str(mat_row.get('MaterialID', '')).strip()
            mat_name = str(mat_row.get('MaterialName', 'Unknown')).strip()

            # Ensure stock and ROP are valid numbers, otherwise skip
            current_stock_str = str(mat_row.get('CurrentStock', '0')).strip()
            reorder_point_str = str(mat_row.get('ReorderPoint', '0')).strip()

            if not current_stock_str or not reorder_point_str:
                 log_message(f"  Skipping {mat_name} (ID: {mat_id}): Missing CurrentStock or ReorderPoint.")
                 continue

            stock = float(current_stock_str)
            rop = float(reorder_point_str)

            log_message(f"Checking: {mat_name} (ID: {mat_id}, Stock: {stock}, ROP: {rop})")
            if stock < rop:
                log_message(f"  Reorder suggested for {mat_name}.")
                sup_id = str(mat_row.get('PreferredSupplierID', '')).strip()

                std_order_qty_str = str(mat_row.get('StandardOrderQuantity', '0')).strip()
                if not std_order_qty_str:
                    log_message(f"  Skipping {mat_name} (ID: {mat_id}): Missing StandardOrderQuantity.")
                    continue
                order_qty = float(std_order_qty_str)

                current_price_str = str(mat_row.get('CurrentPrice', '0.0')).strip()
                if not current_price_str: # Default to 0 if missing, but log?
                    log_message(f"  Warning for {mat_name} (ID: {mat_id}): Missing CurrentPrice, defaulting to 0.0.")
                    price = 0.0
                else:
                    price = float(current_price_str)

                url = str(mat_row.get('ProductPageURL', '')).strip()

                if not sup_id:
                    log_message(f"  Skipping {mat_name} (ID: {mat_id}): Missing PreferredSupplierID.")
                    continue
                if order_qty <= 0:
                    log_message(f"  Skipping {mat_name} (ID: {mat_id}): StandardOrderQuantity is zero or less.")
                    continue

                suggested_orders_list.append({
                    'MaterialID': mat_id,
                    'MaterialName': mat_name,
                    'CurrentStock': stock,
                    'ReorderPoint': rop,
                    'PreferredSupplierID': sup_id,
                    'QuantityToOrder': order_qty,
                    'UnitPrice': price, # Changed from UnitPricePaid
                    'ProductPageURL': url
                })
                log_message(f"  Added {mat_name} (Qty: {order_qty}) for supplier ID {sup_id} to suggestions.")
        except ValueError as ve:
            log_message(f"  Skipping material {mat_row.get('MaterialID', 'Unknown')} due to data error: {ve}")
        except Exception as e: # Catch any other unexpected error for a specific material
            log_message(f"  Unexpected error processing material {mat_row.get('MaterialID', 'Unknown')}: {e}")


    if not suggested_orders_list:
        log_message("\n--- No items require reordering at this time. ---")
    
    log_message(f"\n--- Finished identifying suggested orders. Found {len(suggested_orders_list)} items. ---")
    return suggested_orders_list # Return the list of items, not the log summary directly

def process_single_purchase_order(order_item, supplier_info, logger_func=None):
    # order_item is a dict from the list generated by main()
    # supplier_info is a pd.Series or dict for the specific supplier

    _processing_log_summary = []
    def log_message(message):
        if logger_func:
            logger_func(message)
        else:
            print(message)
        _processing_log_summary.append(str(message))

    sup_id = str(supplier_info.get('SupplierID', 'ERROR_NO_SUP_ID')).strip()
    sup_name = str(supplier_info.get('SupplierName', sup_id)).strip()
    method = str(supplier_info.get('OrderMethod', '')).lower().strip()
    email_address = str(supplier_info.get('Email', '')).strip()
    website_url = str(supplier_info.get('Website', '')).strip() # Renamed for clarity
    phone_number = str(supplier_info.get('Phone', 'N/A')).strip() # Renamed

    log_message(f"\n--- Processing Order for Item: {order_item['MaterialName']} (Supplier: {sup_name}) ---")

    order_id = generate_order_id()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logged_method_status = "" # More descriptive status

    # For email, we need a list containing a single item for generate_po_email_content
    # as it expects a list of items.
    email_item_for_this_order = [{'name': order_item['MaterialName'], 'quantity': order_item['QuantityToOrder']}]

    if method == "email":
        if not email_address:
            logged_method_status = "failed_email_no_address"
            log_message(f"  Error: No email address for {sup_name} (ID: {sup_id}). Cannot send email for {order_item['MaterialName']}.")
        else:
            log_message(f"  Preparing email for {order_item['MaterialName']} (Qty: {order_item['QuantityToOrder']}) to {email_address}...")
            subj, body = generate_po_email_content(sup_name, email_item_for_this_order) # Pass list with single item
            if subj and body:
                log_message(f"  Attempting to send email for {order_item['MaterialName']}...")
                # success = send_po_email(email_address, subj, body) # Actual sending
                success = False # Placeholder for now
                log_message(f"  Email sending function called for {order_item['MaterialName']}. Placeholder success: {success}")
                logged_method_status = f"email_{'sent' if success else 'failed_send_placeholder'}"
            else:
                logged_method_status = "email_failed_content_generation"
                log_message(f"  Error generating email content for {order_item['MaterialName']} to {sup_name}.")
    elif method == "online":
        logged_method_status = "online_manual_order_required"
        item_url = order_item.get('ProductPageURL', '')
        effective_url = item_url if item_url else website_url # Use item specific URL if available
        log_message(f"  Action Required: Place ONLINE order for {order_item['MaterialName']} (Qty: {order_item['QuantityToOrder']}) with {sup_name} via {effective_url if effective_url else 'supplier website (no URL provided)'}.")
    elif method == "phone":
        logged_method_status = "phone_manual_order_required"
        log_message(f"  Action Required: Place PHONE order for {order_item['MaterialName']} (Qty: {order_item['QuantityToOrder']}) with {sup_name} (Phone: {phone_number}).")
    else:
        logged_method_status = f"manual_review_unknown_method ({method})"
        log_message(f"  Warning: Unknown or unspecified OrderMethod ('{method}') for {sup_name}. Manual review needed for {order_item['MaterialName']} (Qty: {order_item['QuantityToOrder']}).")

    history_entry = {
        'OrderID': order_id,
        'Timestamp': timestamp,
        'MaterialID': order_item['MaterialID'],
        'MaterialName': order_item['MaterialName'],
        'QuantityOrdered': order_item['QuantityToOrder'],
        'UnitPricePaid': order_item['UnitPrice'], # Using 'UnitPrice' from suggested order
        'TotalPricePaid': order_item['QuantityToOrder'] * order_item['UnitPrice'],
        'SupplierID': sup_id,
        'SupplierName': sup_name,
        'OrderMethod': logged_method_status, # Use the more descriptive status
        'Status': 'Ordered', # Initial status
        'QuantityReceived': '0',
        'DateReceived': '',
        'Notes': ''
    }

    # This function now returns the history entry and the log of its own execution.
    # The actual logging to CSV is separated.
    log_message(f"--- Finished processing for item: {order_item['MaterialName']}. Status: {logged_method_status} ---")
    return history_entry, _processing_log_summary


def log_order_to_history(order_history_entry, logger_func=None):
    _logging_log_summary = []
    def log_message(message):
        if logger_func:
            logger_func(message)
        else:
            print(message)
        _logging_log_summary.append(str(message))

    if not order_history_entry or not isinstance(order_history_entry, dict):
        log_message("Error: Invalid order history entry provided for logging.")
        return _logging_log_summary

    try:
        # Convert single entry to DataFrame to use append_to_csv
        entry_df = pd.DataFrame([order_history_entry])
        append_to_csv(entry_df, ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS)
        log_message(f"  Successfully logged OrderID {order_history_entry.get('OrderID')} for MaterialID {order_history_entry.get('MaterialID')} to {ORDER_HISTORY_FILE}.")
    except Exception as e:
        log_message(f"  Error logging OrderID {order_history_entry.get('OrderID')} to {ORDER_HISTORY_FILE}: {e}")

    return _logging_log_summary


if __name__ == "__main__":
    # Example of how the new main() and processing functions might be used
    print("Running main.py directly...")

    # Get suggested orders
    # The list of logged messages from main() itself is not captured here, but would be if logger_func was passed
    suggested_orders = main()

    if suggested_orders:
        print(f"\n--- {len(suggested_orders)} Suggested Orders Identified ---")
        for i, item in enumerate(suggested_orders):
            print(f"Suggestion {i+1}:")
            for key, value in item.items():
                print(f"  {key}: {value}")
            print("-" * 20)
        
        # Example: Process the first suggested order (if suppliers_df was loaded)
        # This part is more for demonstration; actual processing would likely be triggered by GUI
        # suppliers_df_main = load_csv_to_dataframe(SUPPLIERS_FILE, SUPPLIERS_HEADERS)
        # if not suggested_orders[0]['PreferredSupplierID'] or suppliers_df_main.empty:
        #     print("\nCannot demonstrate processing: Missing supplier ID or suppliers file is empty.")
        # else:
        #     first_item = suggested_orders[0]
        #     supplier_id_for_item = first_item['PreferredSupplierID']
        #     supplier_details_for_item = suppliers_df_main[suppliers_df_main['SupplierID'] == supplier_id_for_item]
        #     if not supplier_details_for_item.empty:
        #         history_entry_result, processing_logs = process_single_purchase_order(first_item, supplier_details_for_item.iloc[0], logger_func=print)
        #         if history_entry_result:
        #             logging_logs = log_order_to_history(history_entry_result, logger_func=print)
        #     else:
        #         print(f"\nCould not find supplier details for SupplierID: {supplier_id_for_item}")

    else:
        print("\n--- No suggested orders identified. ---")

    print("\n--- Direct execution of main.py finished. ---")
