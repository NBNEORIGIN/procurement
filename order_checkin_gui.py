import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QFormLayout,
    QMessageBox, QSpinBox, QTextEdit, QGroupBox, QHeaderView
)
from PyQt6.QtCore import Qt
import os
from datetime import datetime

ORDER_HISTORY_FILE = "order_history.csv"
MATERIALS_MASTER_FILE = "materials_master.csv"
STOCK_MOVEMENTS_FILE = "stock_movements.csv"

ORDER_HISTORY_HEADERS = ['OrderID', 'Timestamp', 'MaterialID', 'MaterialName', 'QuantityOrdered', 
                         'UnitPricePaid', 'TotalPricePaid', 'SupplierID', 'SupplierName', 
                         'OrderMethod', 'Status', 'Notes']
MATERIALS_HEADERS = ['MaterialID', 'MaterialName', 'Category', 'UnitOfMeasure', 'CurrentStock', 
                     'ReorderPoint', 'StandardOrderQuantity', 'PreferredSupplierID', 
                     'ProductPageURL', 'LeadTimeDays', 'SafetyStockQuantity', 'Notes', 'CurrentPrice']
STOCK_MOVEMENTS_HEADERS = ['MovementID', 'Timestamp', 'MaterialID', 'MaterialName', 
                           'ChangeInQuantity', 'NewStockLevel', 'Reason', 'RelatedOrderID']

def get_int_val(val_str, default=0): # Helper from previous GUI
    try: return int(float(str(val_str))) if pd.notna(val_str) and str(val_str).strip() != '' else default
    except ValueError: return default

def load_or_create_dataframe(file_path, expected_headers, default_dtype=str):
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            df = pd.read_csv(file_path, dtype=default_dtype).fillna('')
            missing_cols = False
            for header in expected_headers:
                if header not in df.columns: df[header] = ''; missing_cols = True
            if missing_cols and os.path.getsize(file_path) > 0 : # Only show if file wasn't just created
                 QMessageBox.information(None,"File Schema Notice", f"File '{file_path}' was missing columns; they've been added.")
            return df[expected_headers].fillna('')
        except Exception as e:
            QMessageBox.critical(None, "Load Error", f"Error loading {file_path}: {e}")
            return pd.DataFrame(columns=expected_headers).astype(default_dtype).fillna('')
    else:
        if not os.path.exists(file_path):
             QMessageBox.information(None, "File Notice", f"File '{file_path}' not found. Creating with headers.")
        elif os.path.getsize(file_path) == 0:
             QMessageBox.information(None, "File Notice", f"File '{file_path}' is empty. Initializing with headers.")
        try:
            df = pd.DataFrame(columns=expected_headers); df.to_csv(file_path, index=False)
            return df.astype(default_dtype).fillna('')
        except Exception as e:
            QMessageBox.critical(None, "File Creation Error", f"Could not create {file_path}: {e}")
            return pd.DataFrame(columns=expected_headers).astype(default_dtype).fillna('')

def append_to_csv(df_to_append, file_path, expected_headers):
    df_ready = pd.DataFrame(columns=expected_headers)
    for col in expected_headers: df_ready[col] = df_to_append.get(col, pd.Series(dtype=str)) # Ensure all columns
    df_ready = df_ready[expected_headers].astype(str) # Ensure string type and order

    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        df_ready.to_csv(file_path, index=False, header=True)
    else:
        df_ready.to_csv(file_path, index=False, header=False, mode='a')

def generate_movement_id(): return f"SM-{datetime.now().strftime('%Y%m%d-%H%M%S%f')[:-3]}"

class OrderCheckInGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Order Check-In System"); self.setGeometry(150, 150, 1000, 600)
        self.order_history_df = load_or_create_dataframe(ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS)
        self.materials_df = load_or_create_dataframe(MATERIALS_MASTER_FILE, MATERIALS_HEADERS)
        load_or_create_dataframe(STOCK_MOVEMENTS_FILE, STOCK_MOVEMENTS_HEADERS) # Ensure it exists
        self.current_selected_order_line_df_index = None # Actual index in self.order_history_df
        self.init_ui(); self.refresh_pending_orders_table()

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QVBoxLayout(central)
        pending_group = QGroupBox("Pending Order Lines (Status: Ordered or Partially Received)"); pending_l = QVBoxLayout()
        self.pending_table = QTableWidget(); self.pending_table.itemSelectionChanged.connect(self.on_order_line_selected)
        pending_l.addWidget(self.pending_table); pending_group.setLayout(pending_l); layout.addWidget(pending_group)

        checkin_group = QGroupBox("Check-In Details"); checkin_form = QFormLayout()
        self.order_id_lbl = QLabel("N/A"); self.mat_lbl = QLabel("N/A"); self.qty_ord_lbl = QLabel("N/A")
        self.qty_rec_spin = QSpinBox(); self.qty_rec_spin.setRange(0, 99999)
        self.notes_edit = QTextEdit(); self.notes_edit.setFixedHeight(60)
        self.proc_btn = QPushButton("Process Receipt"); self.proc_btn.clicked.connect(self.process_receipt); self.proc_btn.setEnabled(False)
        checkin_form.addRow("OrderID:", self.order_id_lbl); checkin_form.addRow("Material:", self.mat_lbl)
        checkin_form.addRow("Qty Ordered:", self.qty_ord_lbl); checkin_form.addRow("Qty Received*:", self.qty_rec_spin)
        checkin_form.addRow("Receipt Notes:", self.notes_edit); checkin_form.addRow(self.proc_btn)
        checkin_group.setLayout(checkin_form); layout.addWidget(checkin_group)

    def refresh_pending_orders_table(self):
        pending_statuses = ["ordered", "partially received"]
        if 'Status' in self.order_history_df.columns:
            # Create a temporary column for case-insensitive comparison
            self.order_history_df['_status_lower'] = self.order_history_df['Status'].str.lower()
            self.display_df = self.order_history_df[self.order_history_df['_status_lower'].isin(pending_statuses)].copy()
            self.order_history_df.drop(columns=['_status_lower'], inplace=True, errors='ignore')
        else: self.display_df = pd.DataFrame(columns=ORDER_HISTORY_HEADERS)
        
        cols = ['OrderID', 'Timestamp', 'MaterialID', 'MaterialName', 'QuantityOrdered', 'SupplierName', 'Status']
        for c in cols: # Ensure columns exist in display_df
            if c not in self.display_df.columns: self.display_df[c] = ""
        
        self.pending_table.setRowCount(self.display_df.shape[0]); self.pending_table.setColumnCount(len(cols))
        self.pending_table.setHorizontalHeaderLabels(cols)
        for r in range(self.display_df.shape[0]):
            for c, col_name in enumerate(cols):
                self.pending_table.setItem(r, c, QTableWidgetItem(str(self.display_df.iloc[r].get(col_name, ''))))
        self.pending_table.resizeColumnsToContents(); self.pending_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pending_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.clear_checkin_form()

    def on_order_line_selected(self):
        rows = self.pending_table.selectionModel().selectedRows()
        if not rows: self.clear_checkin_form(); self.proc_btn.setEnabled(False); return
        
        view_row = rows[0].row()
        # Get OrderID and MaterialID from the selected row in the *displayed table*
        # These are used to find the unique row in the original self.order_history_df
        order_id_val = self.display_df.iloc[view_row]['OrderID']
        mat_id_val = self.display_df.iloc[view_row]['MaterialID']
        
        # Find the original index in self.order_history_df
        original_indices = self.order_history_df[
            (self.order_history_df['OrderID'] == order_id_val) & 
            (self.order_history_df['MaterialID'] == mat_id_val) &
            (self.order_history_df['Status'].str.lower().isin(["ordered", "partially received"]))
        ].index.tolist()

        if not original_indices:
            QMessageBox.warning(self, "Error", "Could not find selected order line in main data. Try refreshing."); self.clear_checkin_form(); return
        
        self.current_selected_order_line_df_index = original_indices[0] # Store actual DataFrame index
        line_data = self.order_history_df.loc[self.current_selected_order_line_df_index]

        self.order_id_lbl.setText(str(line_data.get('OrderID', 'N/A')))
        self.mat_lbl.setText(f"{line_data.get('MaterialName', 'N/A')} (ID: {line_data.get('MaterialID', 'N/A')})")
        qty_ord = str(line_data.get('QuantityOrdered', '0')); self.qty_ord_lbl.setText(qty_ord)
        self.qty_rec_spin.setValue(get_int_val(qty_ord)); self.qty_rec_spin.setMaximum(get_int_val(qty_ord, 99999))
        self.notes_edit.clear(); self.proc_btn.setEnabled(True)

    def clear_checkin_form(self):
        self.order_id_lbl.setText("N/A"); self.mat_lbl.setText("N/A"); self.qty_ord_lbl.setText("N/A")
        self.qty_rec_spin.setValue(0); self.notes_edit.clear()
        self.current_selected_order_line_df_index = None; self.proc_btn.setEnabled(False)
        self.pending_table.clearSelection()

    def process_receipt(self):
        if self.current_selected_order_line_df_index is None: QMessageBox.warning(self, "Error", "No order line selected."); return
        qty_rec = self.qty_rec_spin.value(); notes = self.notes_edit.toPlainText().strip()
        if qty_rec <= 0: QMessageBox.warning(self, "Input Error", "Qty Received must be > 0."); return

        try:
            order_line = self.order_history_df.loc[self.current_selected_order_line_df_index]
            mat_id = str(order_line['MaterialID'])
            mat_rows = self.materials_df[self.materials_df['MaterialID'] == mat_id]
            if mat_rows.empty: QMessageBox.critical(self, "Data Error", f"MaterialID '{mat_id}' not in materials master!"); return
            
            mat_master_idx = mat_rows.index[0]
            stock_val = get_int_val(self.materials_df.loc[mat_master_idx, 'CurrentStock'])
            new_stock = stock_val + qty_rec
            self.materials_df.loc[mat_master_idx, 'CurrentStock'] = str(new_stock)
            
            # Update order_history (simplified: mark as Received)
            self.order_history_df.loc[self.current_selected_order_line_df_index, 'Status'] = "Received"
            current_notes = str(self.order_history_df.loc[self.current_selected_order_line_df_index, 'Notes'])
            self.order_history_df.loc[self.current_selected_order_line_df_index, 'Notes'] = f"{current_notes}; RX {qty_rec} on {datetime.now().strftime('%Y-%m-%d')}: {notes}".strip('; ')

            movement = {'MovementID': generate_movement_id(), 'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'MaterialID': mat_id, 'MaterialName': str(order_line.get('MaterialName', '')),
                        'ChangeInQuantity': str(qty_rec), 'NewStockLevel': str(new_stock),
                        'Reason': f"Order Received PO: {order_line['OrderID']}", 'RelatedOrderID': order_line['OrderID']}
            append_to_csv(pd.DataFrame([movement]), STOCK_MOVEMENTS_FILE, STOCK_MOVEMENTS_HEADERS)
            
            self.save_dataframe(self.materials_df, MATERIALS_MASTER_FILE, MATERIALS_HEADERS)
            self.save_dataframe(self.order_history_df, ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS) # Save entire df
            
            QMessageBox.information(self, "Success", f"Receipt of {qty_rec} for {mat_id} processed.")
            self.refresh_pending_orders_table(); self.clear_checkin_form()
        except Exception as e: QMessageBox.critical(self, "Processing Error", f"Error: {e}")

def save_dataframe(df, file_path, headers_order): # Standalone save for convenience if needed elsewhere
    try:
        df_to_save = df.copy()
        for header in headers_order: 
             if header not in df_to_save.columns: df_to_save[header] = ''
        df_to_save[headers_order].to_csv(file_path, index=False) 
    except Exception as e: print(f"Error saving {file_path} from standalone: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv); win = OrderCheckInGUI(); win.show(); sy
