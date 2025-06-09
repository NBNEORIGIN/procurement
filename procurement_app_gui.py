import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QLineEdit, QPushButton, QLabel, QFormLayout,
    QMessageBox, QComboBox, QSpinBox, QTextEdit, QHeaderView, QDoubleSpinBox,
    QGroupBox, QCheckBox # <--- QCheckBox ADDED HERE
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
import os
from datetime import datetime
from main import append_to_csv

def generate_order_id():
    return f"PO-{datetime.now().strftime('%Y%m%d-%H%M%S%f')[:-3]}"

MATERIALS_FILE = "materials_master.csv"
SUPPLIERS_FILE = "suppliers.csv"
ORDER_HISTORY_FILE = "order_history.csv"

MATERIALS_HEADERS = ['MaterialID', 'MaterialName', 'Category', 'UnitOfMeasure', 'CurrentStock',
                     'ReorderPoint', 'StandardOrderQuantity', 'PreferredSupplierID',
                     'ProductPageURL', 'LeadTimeDays', 'SafetyStockQuantity', 'Notes', 'CurrentPrice']
SUPPLIERS_HEADERS = ['SupplierID', 'SupplierName', 'ContactPerson', 'Email', 'Phone', 'Website', 'OrderMethod']
ORDER_HISTORY_HEADERS = ['OrderID', 'Timestamp', 'MaterialID', 'MaterialName', 'QuantityOrdered',
                         'UnitPricePaid', 'TotalPricePaid', 'SupplierID', 'SupplierName',
                         'OrderMethod', 'Status', 'Notes']

def get_int_val(val_str, default=0):
    try: return int(float(str(val_str))) if pd.notna(val_str) and str(val_str).strip() != '' else default
    except ValueError: return default
def get_float_val(val_str, default=0.0):
    try: return float(str(val_str)) if pd.notna(val_str) and str(val_str).strip() != '' else default
    except ValueError: return default

def load_or_create_dataframe_app(file_path, expected_headers, default_dtype=str, parent_widget=None, create_if_missing=False):
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            df = pd.read_csv(file_path, dtype=default_dtype).fillna('')
            missing_cols = False; current_headers = df.columns.tolist()
            for header in expected_headers:
                if header not in current_headers: df[header] = ''; missing_cols = True
            if missing_cols : QMessageBox.information(parent_widget,"File Schema Notice", f"File '{file_path}' had schema issues; attempted align.")
            return df[expected_headers].fillna('')
        except Exception as e:
            QMessageBox.critical(parent_widget, "Load Error", f"Error loading {file_path}: {e}")
            return pd.DataFrame(columns=expected_headers).astype(default_dtype).fillna('')
    elif create_if_missing:
        if not os.path.exists(file_path): QMessageBox.information(parent_widget, "File Notice", f"'{file_path}' not found. Creating.")
        elif os.path.getsize(file_path) == 0: QMessageBox.information(parent_widget, "File Notice", f"'{file_path}' empty. Initializing.")
        try:
            df = pd.DataFrame(columns=expected_headers); df.to_csv(file_path, index=False)
            return df.astype(default_dtype).fillna('')
        except Exception as e: QMessageBox.critical(parent_widget, "File Creation Error", f"Could not create {file_path}: {e}")
        return pd.DataFrame(columns=expected_headers).astype(default_dtype).fillna('')
    else:
        return pd.DataFrame(columns=expected_headers).astype(default_dtype).fillna('')

class DataManagementWidget(QWidget): # Unchanged from last working version
    def __init__(self, materials_df_ref, suppliers_df_ref, parent_save_cb, parent_refresh_sup_dd_cb):
        super().__init__()
        self.materials_df = materials_df_ref
        self.suppliers_df = suppliers_df_ref
        self.parent_save_cb = parent_save_cb
        self.parent_refresh_sup_dd_cb = parent_refresh_sup_dd_cb
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout(self); self.data_tabs = QTabWidget(); layout.addWidget(self.data_tabs)
        self.materials_tab_widget = QWidget(); self.data_tabs.addTab(self.materials_tab_widget, "Materials Master")
        mat_layout = QVBoxLayout(self.materials_tab_widget)
        self.materials_table_view = QTableWidget(); self.materials_table_view.itemSelectionChanged.connect(self.on_material_selected)
        mat_layout.addWidget(self.materials_table_view)
        mat_form_group = QGroupBox("Material Details"); mat_form = QFormLayout()
        self.mat_id_edit = QLineEdit(); self.mat_name_edit = QLineEdit(); self.mat_cat_edit = QLineEdit(); self.mat_uom_edit = QLineEdit()
        self.mat_stock_spin = QSpinBox(); self.mat_stock_spin.setRange(0,999999); self.mat_rop_spin = QSpinBox(); self.mat_rop_spin.setRange(0,999999)
        self.mat_soq_spin = QSpinBox(); self.mat_soq_spin.setRange(0,999999); self.mat_price_spin = QDoubleSpinBox(); self.mat_price_spin.setRange(0,99999.99); self.mat_price_spin.setDecimals(2); self.mat_price_spin.setPrefix("£")
        self.mat_pref_sup_combo = QComboBox()
        self.mat_url_edit = QLineEdit(); self.mat_url_open_btn = QPushButton("Open Link"); self.mat_url_open_btn.clicked.connect(self.open_material_url)
        mat_url_layout = QHBoxLayout(); mat_url_layout.addWidget(self.mat_url_edit); mat_url_layout.addWidget(self.mat_url_open_btn)
        self.mat_lead_spin = QSpinBox(); self.mat_lead_spin.setRange(0,365); self.mat_safe_stock_spin = QSpinBox(); self.mat_safe_stock_spin.setRange(0,999999)
        self.mat_notes_edit = QTextEdit(); self.mat_notes_edit.setFixedHeight(60)
        for label, field in [("MaterialID*:", self.mat_id_edit), ("MaterialName*:", self.mat_name_edit), ("Category:", self.mat_cat_edit), ("Unit of Measure:", self.mat_uom_edit),
                             ("Current Stock:", self.mat_stock_spin), ("Reorder Point:", self.mat_rop_spin), ("Std. Order Qty:", self.mat_soq_spin), ("Current Price:", self.mat_price_spin),
                             ("Preferred SupplierID:", self.mat_pref_sup_combo), ("Product Page URL:", mat_url_layout), ("Lead Time (Days):", self.mat_lead_spin),
                             ("Safety Stock Qty:", self.mat_safe_stock_spin), ("Notes:", self.mat_notes_edit)]: mat_form.addRow(label, field)
        mat_form_group.setLayout(mat_form); mat_layout.addWidget(mat_form_group)
        mat_btns_layout = QHBoxLayout();
        for text, method in [("Add New Material", self.add_new_material), ("Save Material", self.save_material),
                             ("Delete Material", self.delete_material), ("Clear Material Form", self.clear_material_form)]:
            btn = QPushButton(text); btn.clicked.connect(method); mat_btns_layout.addWidget(btn)
        mat_layout.addLayout(mat_btns_layout)
        self.suppliers_tab_widget = QWidget(); self.data_tabs.addTab(self.suppliers_tab_widget, "Suppliers")
        sup_layout = QVBoxLayout(self.suppliers_tab_widget)
        self.suppliers_table_view = QTableWidget(); self.suppliers_table_view.itemSelectionChanged.connect(self.on_supplier_selected_from_table)
        sup_layout.addWidget(self.suppliers_table_view)
        sup_form_group = QGroupBox("Supplier Details"); sup_form_details = QFormLayout()
        self.sup_id_edit = QLineEdit(); self.sup_name_edit = QLineEdit(); self.sup_contact_edit = QLineEdit()
        self.sup_email_edit = QLineEdit(); self.sup_phone_edit = QLineEdit()
        self.sup_website_edit = QLineEdit(); self.sup_website_open_btn = QPushButton("Open Link"); self.sup_website_open_btn.clicked.connect(self.open_supplier_website)
        sup_website_layout = QHBoxLayout(); sup_website_layout.addWidget(self.sup_website_edit); sup_website_layout.addWidget(self.sup_website_open_btn)
        self.sup_order_method_combo = QComboBox(); self.sup_order_method_combo.addItems(["", "email", "online", "phone", "other"])
        for label, field in [("SupplierID*:", self.sup_id_edit), ("SupplierName*:", self.sup_name_edit), ("Contact Person:", self.sup_contact_edit),
                             ("Email:", self.sup_email_edit), ("Phone:", self.sup_phone_edit), ("Website:", sup_website_layout),
                             ("Order Method:", self.sup_order_method_combo)]: sup_form_details.addRow(label, field)
        sup_form_group.setLayout(sup_form_details); sup_layout.addWidget(sup_form_group)
        sup_btns_layout = QHBoxLayout()
        for text, method in [("Add New Supplier", self.add_new_supplier), ("Save Supplier", self.save_supplier),
                             ("Delete Supplier", self.delete_supplier), ("Clear Supplier Form", self.clear_supplier_form)]:
            btn = QPushButton(text); btn.clicked.connect(method); sup_btns_layout.addWidget(btn)
        sup_layout.addLayout(sup_btns_layout)
    def open_material_url(self):
        url_string = self.mat_url_edit.text().strip()
        if not url_string: QMessageBox.information(self, "No URL", "Product Page URL field is empty."); return
        if not url_string.startswith(('http://', 'https://')): url_string = 'http://' + url_string
        if not QDesktopServices.openUrl(QUrl(url_string)): QMessageBox.warning(self, "Open URL Failed", f"Could not open URL: {url_string}")
    def open_supplier_website(self):
        url_string = self.sup_website_edit.text().strip()
        if not url_string: QMessageBox.information(self, "No URL", "Supplier Website field is empty."); return
        if not url_string.startswith(('http://', 'https://')): url_string = 'http://' + url_string
        if not QDesktopServices.openUrl(QUrl(url_string)): QMessageBox.warning(self, "Open URL Failed", f"Could not open URL: {url_string}")
    def populate_preferred_supplier_dropdown(self):
        current_selection = self.mat_pref_sup_combo.currentData()
        self.mat_pref_sup_combo.clear(); self.mat_pref_sup_combo.addItem("", None)
        if not self.suppliers_df.empty and 'SupplierID' in self.suppliers_df.columns:
            for _, row in self.suppliers_df.iterrows():
                sid = str(row['SupplierID']); sname = str(row['SupplierName'])
                if sid: self.mat_pref_sup_combo.addItem(f"{sid} : {sname if sname else 'N/A'}", sid)
        if current_selection:
            index = self.mat_pref_sup_combo.findData(current_selection)
            if index != -1: self.mat_pref_sup_combo.setCurrentIndex(index)
    def refresh_materials_table(self):
        if self.materials_df is None: return
        for header in MATERIALS_HEADERS:
            if header not in self.materials_df.columns: self.materials_df[header] = ''
        display_df = self.materials_df[MATERIALS_HEADERS].fillna('')
        self.materials_table_view.setRowCount(display_df.shape[0]); self.materials_table_view.setColumnCount(len(MATERIALS_HEADERS))
        self.materials_table_view.setHorizontalHeaderLabels(MATERIALS_HEADERS);self.materials_table_view.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        for i in range(display_df.shape[0]):
            for j, header in enumerate(MATERIALS_HEADERS): self.materials_table_view.setItem(i, j, QTableWidgetItem(str(display_df.iloc[i].get(header, ''))))
        self.materials_table_view.resizeColumnsToContents(); self.materials_table_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    def on_material_selected(self):
        rows = self.materials_table_view.selectionModel().selectedRows()
        if not rows:
            self.clear_material_form()
            return

        selected_row_index_in_view = rows[0].row()
        # Ensure 'MaterialID' is a defined constant or directly use the string
        material_id_col_idx = MATERIALS_HEADERS.index('MaterialID')
        mat_id_item = self.materials_table_view.item(selected_row_index_in_view, material_id_col_idx)

        if not mat_id_item or not mat_id_item.text():
            self.clear_material_form()
            return

        material_id = mat_id_item.text() # Variable `material_id` is defined

        # CORRECTED: Use the variable `material_id` (defined above)
        data_rows = self.materials_df[self.materials_df['MaterialID'] == material_id]

        if data_rows.empty:
            self.clear_material_form()
            # Optional: QMessageBox.warning(self, "Data Sync Error", f"MaterialID '{material_id}' not found in DataFrame.")
            return  # Explicitly return if no data found

        data = data_rows.iloc[0] # This line should now be safe

        self.mat_id_edit.setText(str(data.get('MaterialID',''))); self.mat_id_edit.setReadOnly(True)
        self.mat_name_edit.setText(str(data.get('MaterialName','')))
        self.mat_cat_edit.setText(str(data.get('Category',''))); self.mat_uom_edit.setText(str(data.get('UnitOfMeasure','')))

        self.mat_stock_spin.setValue(get_int_val(data.get('CurrentStock')))
        self.mat_rop_spin.setValue(get_int_val(data.get('ReorderPoint')))
        self.mat_soq_spin.setValue(get_int_val(data.get('StandardOrderQuantity')))
        self.mat_price_spin.setValue(get_float_val(data.get('CurrentPrice')))

        pref_sup_id_val = str(data.get('PreferredSupplierID',''))
        found_index = self.mat_pref_sup_combo.findData(pref_sup_id_val)
        if found_index != -1: self.mat_pref_sup_combo.setCurrentIndex(found_index)
        else: self.mat_pref_sup_combo.setCurrentIndex(0)

        self.mat_url_edit.setText(str(data.get('ProductPageURL','')))
        self.mat_lead_spin.setValue(get_int_val(data.get('LeadTimeDays')))
        self.mat_safe_stock_spin.setValue(get_int_val(data.get('SafetyStockQuantity')))
        self.mat_notes_edit.setText(str(data.get('Notes','')))
    def clear_material_form(self):
        self.mat_id_edit.clear(); self.mat_id_edit.setReadOnly(False); self.mat_id_edit.setPlaceholderText("Unique ID*")
        for e in [self.mat_name_edit,self.mat_cat_edit,self.mat_uom_edit,self.mat_url_edit,self.mat_notes_edit]: e.clear()
        for s in [self.mat_stock_spin,self.mat_rop_spin,self.mat_soq_spin,self.mat_lead_spin,self.mat_safe_stock_spin]: s.setValue(0)
        self.mat_price_spin.setValue(0.0); self.mat_pref_sup_combo.setCurrentIndex(0); self.materials_table_view.clearSelection()
    def add_new_material(self): self.clear_material_form(); self.mat_id_edit.setFocus()
    def save_material(self):
        mat_id=self.mat_id_edit.text().strip(); mat_name=self.mat_name_edit.text().strip()
        if not mat_id or not mat_name: QMessageBox.warning(self,"Input Error","ID and Name required."); return
        pref_sup_id_val=self.mat_pref_sup_combo.currentData() or ""
        data_dict = {h:"" for h in MATERIALS_HEADERS}
        data_dict.update({'MaterialID':mat_id, 'MaterialName':mat_name, 'Category':self.mat_cat_edit.text().strip(),
                          'UnitOfMeasure':self.mat_uom_edit.text().strip(), 'CurrentStock':str(self.mat_stock_spin.value()),
                          'ReorderPoint':str(self.mat_rop_spin.value()), 'StandardOrderQuantity':str(self.mat_soq_spin.value()),
                          'CurrentPrice':"%.2f"%self.mat_price_spin.value(), 'PreferredSupplierID':pref_sup_id_val,
                          'ProductPageURL':self.mat_url_edit.text().strip(), 'LeadTimeDays':str(self.mat_lead_spin.value()),
                          'SafetyStockQuantity':str(self.mat_safe_stock_spin.value()), 'Notes':self.mat_notes_edit.toPlainText().strip()})
        existing = self.materials_df.index[self.materials_df['MaterialID'] == mat_id].tolist()
        if existing: self.materials_df.loc[existing[0]] = pd.Series(data_dict)
        else: self.materials_df = pd.concat([self.materials_df, pd.DataFrame([data_dict], columns=MATERIALS_HEADERS)], ignore_index=True)
        self.parent_save_cb(MATERIALS_FILE, self.materials_df, MATERIALS_HEADERS)
        self.refresh_materials_table(); self.clear_material_form()
    def delete_material(self):
        rows=self.materials_table_view.selectionModel().selectedRows()
        if not rows: QMessageBox.warning(self,"Selection Error","Select material to delete."); return
        idx=MATERIALS_HEADERS.index('MaterialID'); mat_id_del=self.materials_table_view.item(rows[0].row(),idx).text()
        if QMessageBox.question(self,"Confirm",f"Delete '{mat_id_del}'?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.materials_df = self.materials_df[self.materials_df['MaterialID'] != mat_id_del].reset_index(drop=True)
            self.parent_save_cb(MATERIALS_FILE, self.materials_df, MATERIALS_HEADERS)
            self.refresh_materials_table(); self.clear_material_form()
    def refresh_suppliers_table(self):
        if self.suppliers_df is None: return
        for header in SUPPLIERS_HEADERS:
            if header not in self.suppliers_df.columns: self.suppliers_df[header] = ''
        display_df = self.suppliers_df[SUPPLIERS_HEADERS].fillna('')
        self.suppliers_table_view.setRowCount(display_df.shape[0]); self.suppliers_table_view.setColumnCount(len(SUPPLIERS_HEADERS))
        self.suppliers_table_view.setHorizontalHeaderLabels(SUPPLIERS_HEADERS); self.suppliers_table_view.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        for i in range(display_df.shape[0]):
            for j, header in enumerate(SUPPLIERS_HEADERS): self.suppliers_table_view.setItem(i, j, QTableWidgetItem(str(display_df.iloc[i].get(header, ''))))
        self.suppliers_table_view.resizeColumnsToContents(); self.suppliers_table_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # self.parent_refresh_sup_dd_cb() # This is called by parent app after this refresh is done via parent_save_cb
    def on_supplier_selected_from_table(self):
        rows=self.suppliers_table_view.selectionModel().selectedRows()
        if not rows: self.clear_supplier_form(); return
        idx=SUPPLIERS_HEADERS.index('SupplierID'); sup_id_item=self.suppliers_table_view.item(rows[0].row(),idx)
        if not sup_id_item or not sup_id_item.text(): self.clear_supplier_form(); return; supplier_id=sup_id_item.text()
        data_rows=self.suppliers_df[self.suppliers_df['SupplierID']==supplier_id]
        if data_rows.empty: self.clear_supplier_form(); return; data=data_rows.iloc[0]
        self.sup_id_edit.setText(str(data.get('SupplierID',''))); self.sup_id_edit.setReadOnly(True); self.sup_name_edit.setText(str(data.get('SupplierName','')))
        self.sup_contact_edit.setText(str(data.get('ContactPerson',''))); self.sup_email_edit.setText(str(data.get('Email','')))
        self.sup_phone_edit.setText(str(data.get('Phone',''))); self.sup_website_edit.setText(str(data.get('Website','')))
        self.sup_order_method_combo.setCurrentText(str(data.get('OrderMethod','')))
    def clear_supplier_form(self):
        self.sup_id_edit.clear(); self.sup_id_edit.setReadOnly(False); self.sup_id_edit.setPlaceholderText("Unique ID*")
        for e in [self.sup_name_edit,self.sup_contact_edit,self.sup_email_edit,self.sup_phone_edit,self.sup_website_edit]: e.clear()
        self.sup_order_method_combo.setCurrentIndex(0); self.suppliers_table_view.clearSelection()
    def add_new_supplier(self): self.clear_supplier_form(); self.sup_id_edit.setFocus()
    def save_supplier(self):
        sup_id=self.sup_id_edit.text().strip(); sup_name=self.sup_name_edit.text().strip()
        if not sup_id or not sup_name: QMessageBox.warning(self,"Input Error","SupplierID and Name required."); return
        data_dict = {h:"" for h in SUPPLIERS_HEADERS}
        data_dict.update({'SupplierID':sup_id, 'SupplierName':sup_name, 'ContactPerson':self.sup_contact_edit.text().strip(),
                          'Email':self.sup_email_edit.text().strip(), 'Phone':self.sup_phone_edit.text().strip(),
                          'Website':self.sup_website_edit.text().strip(), 'OrderMethod':self.sup_order_method_combo.currentText()})
        existing=self.suppliers_df.index[self.suppliers_df['SupplierID']==sup_id].tolist()
        if existing: self.suppliers_df.loc[existing[0]] = pd.Series(data_dict)
        else: self.suppliers_df=pd.concat([self.suppliers_df, pd.DataFrame([data_dict], columns=SUPPLIERS_HEADERS)], ignore_index=True)
        self.parent_save_cb(SUPPLIERS_FILE, self.suppliers_df, SUPPLIERS_HEADERS)
        self.refresh_suppliers_table(); self.clear_supplier_form()
        self.parent_refresh_sup_dd_cb()
    def delete_supplier(self):
        rows=self.suppliers_table_view.selectionModel().selectedRows()
        if not rows: QMessageBox.warning(self,"Selection Error","Select supplier to delete."); return
        idx=SUPPLIERS_HEADERS.index('SupplierID'); sup_id_del=self.suppliers_table_view.item(rows[0].row(),idx).text()
        if not self.materials_df.empty and 'PreferredSupplierID' in self.materials_df.columns:
            if sup_id_del in self.materials_df['PreferredSupplierID'].values:
                used_by=self.materials_df[self.materials_df['PreferredSupplierID']==sup_id_del]['MaterialID'].tolist()
                QMessageBox.warning(self,"Deletion Error",f"Supplier '{sup_id_del}' used by: {', '.join(used_by)}. Update materials first.")
                return
        if QMessageBox.question(self,"Confirm",f"Delete '{sup_id_del}'?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.suppliers_df = self.suppliers_df[self.suppliers_df['SupplierID']!=sup_id_del].reset_index(drop=True)
            self.parent_save_cb(SUPPLIERS_FILE, self.suppliers_df, SUPPLIERS_HEADERS)
            self.refresh_suppliers_table(); self.clear_supplier_form()
            self.parent_refresh_sup_dd_cb()

class ProcurementAppGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Integrated Procurement Application")
        self.setGeometry(50, 50, 1200, 850)

        self.materials_df = load_or_create_dataframe_app(MATERIALS_FILE, MATERIALS_HEADERS, parent_widget=self, create_if_missing=True)
        self.suppliers_df = load_or_create_dataframe_app(SUPPLIERS_FILE, SUPPLIERS_HEADERS, parent_widget=self, create_if_missing=True)
        self.order_history_df = load_or_create_dataframe_app(ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS, create_if_missing=True, parent_widget=self)
        
        self.main_tabs = QTabWidget(); self.setCentralWidget(self.main_tabs)
        self.data_management_widget = DataManagementWidget(self.materials_df,self.suppliers_df,self.save_any_dataframe,self.refresh_preferred_supplier_dropdown_in_materials_tab)
        self.main_tabs.addTab(self.data_management_widget, "Data Management Hub")
        
        self.generate_orders_tab = QWidget(); self.main_tabs.addTab(self.generate_orders_tab, "Generate Orders")
        gen_ord_layout = QVBoxLayout(self.generate_orders_tab)
        gen_ord_top_btn_layout = QHBoxLayout()
        self.run_order_check_button = QPushButton("Refresh / Prepare Draft Orders"); self.run_order_check_button.clicked.connect(self.prepare_orders_action)
        gen_ord_top_btn_layout.addWidget(self.run_order_check_button)
        self.process_selected_orders_button = QPushButton("Process Selected Orders"); self.process_selected_orders_button.clicked.connect(self.process_selected_orders_action); self.process_selected_orders_button.setEnabled(False) 
        gen_ord_top_btn_layout.addWidget(self.process_selected_orders_button); gen_ord_top_btn_layout.addStretch(); gen_ord_layout.addLayout(gen_ord_top_btn_layout)
        self.proposed_orders_table = QTableWidget()
        self.proposed_orders_cols = ["Select", "SupplierName", "SupplierID", "MaterialID", "MaterialName", "OrderQty", "Unit Price", "Total Price", "OrderMethod", "ActionDetails", "Open Link"]
        self.proposed_orders_table.setColumnCount(len(self.proposed_orders_cols)); self.proposed_orders_table.setHorizontalHeaderLabels(self.proposed_orders_cols)
        self.proposed_orders_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); gen_ord_layout.addWidget(self.proposed_orders_table)
        self.order_process_log = QTextEdit(); self.order_process_log.setReadOnly(True); self.order_process_log.setFixedHeight(150)
        gen_ord_layout.addWidget(QLabel("Processing Log:")); gen_ord_layout.addWidget(self.order_process_log)
        
        self.order_checkin_tab = QWidget(); self.main_tabs.addTab(self.order_checkin_tab, "Order Check-In (TBD)")
        self.order_checkin_tab.setLayout(QVBoxLayout()); self.order_checkin_tab.layout().addWidget(QLabel("Order check-in functionality will be integrated here."))
        
        self.data_management_widget.populate_preferred_supplier_dropdown()
        self.data_management_widget.refresh_materials_table(); self.data_management_widget.refresh_suppliers_table()

    # generate_order_id is NOT a method here, it's a module-level function now.
    # No @staticmethod needed if it's outside the class.

    def save_any_dataframe(self, file_path, df, headers_order):
        # ... (This method should be correct from your last working version)
        try:
            df_to_save = df.copy()
            for header in headers_order:
                 if header not in df_to_save.columns: df_to_save[header] = ''
            df_to_save[headers_order].to_csv(file_path, index=False)
            QMessageBox.information(self, "Success", f"Data saved to {file_path}")
            if file_path == SUPPLIERS_FILE: 
                self.suppliers_df = df.copy() 
                if hasattr(self, 'data_management_widget'): self.data_management_widget.suppliers_df = self.suppliers_df 
                self.refresh_preferred_supplier_dropdown_in_materials_tab()
            elif file_path == MATERIALS_FILE: 
                self.materials_df = df.copy() 
                if hasattr(self, 'data_management_widget'): self.data_management_widget.materials_df = self.materials_df
            elif file_path == ORDER_HISTORY_FILE: 
                self.order_history_df = df.copy() 
        except Exception as e: QMessageBox.critical(self, "Save Error", f"Error saving to {file_path} (App): {e}")


    def refresh_preferred_supplier_dropdown_in_materials_tab(self):
        # ... (This method should be correct from your last working version)
        if hasattr(self, 'data_management_widget'): self.data_management_widget.populate_preferred_supplier_dropdown()


    def prepare_orders_action(self):
        # ... (This method should be correct from your last working version)
        self.order_process_log.clear(); self.proposed_orders_table.setRowCount(0)
        self.order_process_log.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Starting order prep...")
        current_materials_df = self.materials_df; current_suppliers_df = self.suppliers_df
        if current_materials_df.empty: self.order_process_log.append("Error: Materials empty."); return
        items_to_order_by_supplier_id = {} 
        for _, mat_row in current_materials_df.iterrows():
            try:
                mat_id = str(mat_row.get('MaterialID','')).strip(); mat_name = str(mat_row.get('MaterialName','U')).strip()
                stock = get_float_val(str(mat_row.get('CurrentStock','0')),0.0); rop = get_float_val(str(mat_row.get('ReorderPoint','inf')),float('inf'))
                if stock < rop:
                    pref_sup_id=str(mat_row.get('PreferredSupplierID','')).strip(); order_qty=get_float_val(str(mat_row.get('StandardOrderQuantity','0')),0.0)
                    price=get_float_val(str(mat_row.get('CurrentPrice','0')),0.0); url=str(mat_row.get('ProductPageURL','')).strip()
                    if not pref_sup_id or order_qty <= 0: self.order_process_log.append(f"  Skip {mat_name}: No SupID or 0 Qty."); continue
                    items_to_order_by_supplier_id.setdefault(pref_sup_id,[]).append({'MaterialID':mat_id,'MaterialName':mat_name,'QuantityOrdered':order_qty,'UnitPricePaid':price,'ProductPageURL':url})
            except Exception as e: self.order_process_log.append(f"  Error processing {mat_row.get('MaterialID','Unknown')}: {e}")
        if not items_to_order_by_supplier_id: self.order_process_log.append("No items to reorder."); return
        self.order_process_log.append("Populating proposed orders table..."); self.proposed_orders_table.setRowCount(0)
        for sup_id, items in items_to_order_by_supplier_id.items():
            sup_info_rows=current_suppliers_df[current_suppliers_df['SupplierID']==sup_id]
            if sup_info_rows.empty: self.order_process_log.append(f"  WARN: SupID '{sup_id}' not found for items: {[i['MaterialName'] for i in items]}."); continue
            sup_info=sup_info_rows.iloc[0]; sup_name=str(sup_info.get('SupplierName',sup_id)); method=str(sup_info.get('OrderMethod','N/A')).lower().strip()
            for item_dict in items:
                r=self.proposed_orders_table.rowCount(); self.proposed_orders_table.insertRow(r)
                col_idx_select = self.proposed_orders_cols.index("Select"); chkbox = QCheckBox(); self.proposed_orders_table.setCellWidget(r, col_idx_select, chkbox)
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("SupplierName"),QTableWidgetItem(sup_name))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("SupplierID"),QTableWidgetItem(sup_id))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("MaterialID"),QTableWidgetItem(item_dict['MaterialID']))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("MaterialName"),QTableWidgetItem(item_dict['MaterialName']))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("OrderQty"),QTableWidgetItem(str(item_dict['QuantityOrdered'])))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("Unit Price"),QTableWidgetItem(f"{item_dict['UnitPricePaid']:.2f}"))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("Total Price"),QTableWidgetItem(f"{(item_dict['QuantityOrdered']*item_dict['UnitPricePaid']):.2f}"))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("OrderMethod"),QTableWidgetItem(method))
                action_str=""; url_btn_visible=False; url_to_open = ""
                if method=="email": action_str=f"Email: {sup_info.get('Email','N/A')}"
                elif method=="online": 
                    item_url=item_dict['ProductPageURL']; sup_web=sup_info.get('SupplierWebsite','N/A'); url_to_open=item_url if item_url else sup_web
                    action_str=f"Online order at: {url_to_open if url_to_open else 'N/A'}"; url_btn_visible=bool(url_to_open)
                elif method=="phone": action_str=f"Phone: {sup_info.get('Phone','N/A')}"
                else: action_str="Manual Review"
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("ActionDetails"),QTableWidgetItem(action_str))
                if url_btn_visible:
                    btn=QPushButton("Open"); btn.clicked.connect(lambda chk=False, u=url_to_open: self.open_url_action(u))
                    self.proposed_orders_table.setCellWidget(r,self.proposed_orders_cols.index("Open Link"),btn)
                else: self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("Open Link"),QTableWidgetItem(""))
        self.proposed_orders_table.resizeColumnsToContents(); self.order_process_log.append("Order prep complete.")
        self.process_selected_orders_button.setEnabled(True if self.proposed_orders_table.rowCount() > 0 else False)

    def open_url_action(self, url_string):
        # ... (This method should be correct from your last working version)
        if not url_string: QMessageBox.information(self, "No URL", "No URL available."); return
        if not url_string.startswith(('http://','https://')): url_string='http://'+url_string
        if not QDesktopServices.openUrl(QUrl(url_string)): QMessageBox.warning(self,"Open URL Failed",f"Could not open: {url_string}")

    def process_selected_orders_action(self):
        self.order_process_log.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Processing selected orders...")
        selected_count = 0
        orders_to_log_and_action = [] 
        for r in range(self.proposed_orders_table.rowCount()):
            checkbox = self.proposed_orders_table.cellWidget(r, self.proposed_orders_cols.index("Select"))
            if checkbox and checkbox.isChecked():
                selected_count +=1
                supplier_id = self.proposed_orders_table.item(r, self.proposed_orders_cols.index("SupplierID")).text()
                supplier_name = self.proposed_orders_table.item(r, self.proposed_orders_cols.index("SupplierName")).text()
                material_id = self.proposed_orders_table.item(r, self.proposed_orders_cols.index("MaterialID")).text()
                material_name = self.proposed_orders_table.item(r, self.proposed_orders_cols.index("MaterialName")).text()
                qty_ordered = get_float_val(self.proposed_orders_table.item(r, self.proposed_orders_cols.index("OrderQty")).text())
                unit_price = get_float_val(self.proposed_orders_table.item(r, self.proposed_orders_cols.index("Unit Price")).text())
                order_method = self.proposed_orders_table.item(r, self.proposed_orders_cols.index("OrderMethod")).text()
                orders_to_log_and_action.append({
                    "SupplierID": supplier_id, "SupplierName": supplier_name, "MaterialID": material_id, 
                    "MaterialName": material_name, "QuantityOrdered": qty_ordered, "UnitPricePaid": unit_price,
                    "OrderMethod": order_method,
                    "ActionDetail": self.proposed_orders_table.item(r, self.proposed_orders_cols.index("ActionDetails")).text()
                })
        if not orders_to_log_and_action: self.order_process_log.append("No orders were selected."); return
        self.order_process_log.append(f"Found {len(orders_to_log_and_action)} selected lines.")
        grouped_for_email = {}; new_history_entries = []
        
        # batch_order_id = self.generate_order_id() # If it were a static method of this class
        batch_order_id = generate_order_id() # Calling module-level function
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for order_detail in orders_to_log_and_action:
            history_entry = {
                'OrderID': batch_order_id, 'Timestamp': timestamp, 'MaterialID': order_detail['MaterialID'], 
                'MaterialName': order_detail['MaterialName'], 'QuantityOrdered': order_detail['QuantityOrdered'],
                'UnitPricePaid': order_detail['UnitPricePaid'], 'TotalPricePaid': order_detail['QuantityOrdered'] * order_detail['UnitPricePaid'],
                'SupplierID': order_detail["SupplierID"], 'SupplierName': order_detail['SupplierName'],
                'OrderMethod': order_detail['OrderMethod'], 'Status': 'Ordered', 'Notes': 'Processed via GUI selection.'
            }
            new_history_entries.append(history_entry)
            if order_detail['OrderMethod'] == "email":
                grouped_for_email.setdefault(order_detail["SupplierID"], []).append({'name': order_detail['MaterialName'], 'quantity': order_detail['QuantityOrdered']})
            elif order_detail['OrderMethod'] == "online": self.order_process_log.append(f"  CONFIRMED online: {order_detail['MaterialName']} from {order_detail['SupplierName']}. Details: {order_detail['ActionDetail']}")
            elif order_detail['OrderMethod'] == "phone": self.order_process_log.append(f"  CONFIRMED for phone order: {order_detail['MaterialName']} from {order_detail['SupplierName']}. Details: {order_detail['ActionDetail']}")
            else: self.order_process_log.append(f"  CONFIRMED for manual review: {order_detail['MaterialName']} from {order_detail['SupplierName']}. Details: {order_detail['ActionDetail']}")
        
        from action import generate_po_email_content, send_po_email 
        for supplier_id, items_for_email in grouped_for_email.items():
            supplier_info_rows = self.suppliers_df[self.suppliers_df['SupplierID'] == supplier_id]
            if not supplier_info_rows.empty:
                supplier_info = supplier_info_rows.iloc[0]; supplier_name = str(supplier_info.get('SupplierName', supplier_id)); supplier_email = str(supplier_info.get('Email','')).strip()
                if supplier_email:
                    self.order_process_log.append(f"  Generating email for {supplier_name} ({len(items_for_email)} items)...")
                    subject, body = generate_po_email_content(supplier_name, items_for_email)
                    if subject and body:
                        success = send_po_email(supplier_email, subject, body)
                        log_method_outcome = "email_sent" if success else "email_failed_send"
                        self.order_process_log.append(f"    Email to {supplier_name} {'succeeded' if success else 'failed'}.")
                        for entry in new_history_entries:
                            if entry['SupplierID'] == supplier_id and entry['OrderMethod'] == 'email': entry['OrderMethod'] = log_method_outcome
                    else:
                        self.order_process_log.append(f"    FAILED to generate email content for {supplier_name}.")
                        for entry in new_history_entries:
                            if entry['SupplierID'] == supplier_id and entry['OrderMethod'] == 'email': entry['OrderMethod'] = "email_failed_content"
                else:
                    self.order_process_log.append(f"  SKIPPED email for {supplier_name}: No email address found.")
                    for entry in new_history_entries:
                            if entry['SupplierID'] == supplier_id and entry['OrderMethod'] == 'email': entry['OrderMethod'] = "email_failed_no_address"
        if new_history_entries:
            history_df_to_append = pd.DataFrame(new_history_entries)
            append_to_csv(history_df_to_append, ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS)
            self.order_process_log.append(f"Logged {len(new_history_entries)} lines to {ORDER_HISTORY_FILE} (OrderID: {batch_order_id}).")
            self.order_history_df = load_or_create_dataframe_app(ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS, parent_widget=self, create_if_missing=True)
        self.order_process_log.append("Finished processing selected orders.")
        self.prepare_orders_action(); self.process_selected_orders_button.setEnabled(self.proposed_orders_table.rowCount() > 0)

# if __name__ == '__main__': block as before
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_app_window = ProcurementAppGUI()
    main_app_window.show()
    sys.exit(app.exec())

    def save_any_dataframe(self, file_path, df, headers_order):
        try:
            df_to_save = df.copy()
            for header in headers_order:
                 if header not in df_to_save.columns: df_to_save[header] = ''
            df_to_save[headers_order].to_csv(file_path, index=False)
            QMessageBox.information(self, "Success", f"Data saved to {file_path}")
            if file_path == SUPPLIERS_FILE:
                self.suppliers_df = df.copy(); self.data_management_widget.suppliers_df = self.suppliers_df
                self.refresh_preferred_supplier_dropdown_in_materials_tab()
            elif file_path == MATERIALS_FILE:
                self.materials_df = df.copy(); self.data_management_widget.materials_df = self.materials_df
            elif file_path == ORDER_HISTORY_FILE: self.order_history_df = df.copy()
        except Exception as e: QMessageBox.critical(self, "Save Error", f"Error saving to {file_path} (App): {e}")

    def refresh_preferred_supplier_dropdown_in_materials_tab(self):
        if hasattr(self, 'data_management_widget'): self.data_management_widget.populate_preferred_supplier_dropdown()

    def prepare_orders_action(self):
        self.order_process_log.clear(); self.proposed_orders_table.setRowCount(0)
        self.order_process_log.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Starting order prep...")
        current_materials_df = self.materials_df; current_suppliers_df = self.suppliers_df
        if current_materials_df.empty: self.order_process_log.append("Error: Materials empty."); return
        items_to_order_by_supplier_id = {}
        for _, mat_row in current_materials_df.iterrows():
            try:
                mat_id = str(mat_row.get('MaterialID','')).strip(); mat_name = str(mat_row.get('MaterialName','U')).strip()
                stock = get_float_val(str(mat_row.get('CurrentStock','0')),0.0); rop = get_float_val(str(mat_row.get('ReorderPoint','inf')),float('inf'))
                if stock < rop:
                    pref_sup_id=str(mat_row.get('PreferredSupplierID','')).strip(); order_qty=get_float_val(str(mat_row.get('StandardOrderQuantity','0')),0.0)
                    price=get_float_val(str(mat_row.get('CurrentPrice','0')),0.0); url=str(mat_row.get('ProductPageURL','')).strip()
                    if not pref_sup_id or order_qty <= 0: self.order_process_log.append(f"  Skip {mat_name}: No SupID or 0 Qty."); continue
                    items_to_order_by_supplier_id.setdefault(pref_sup_id,[]).append({'MaterialID':mat_id,'MaterialName':mat_name,'QuantityOrdered':order_qty,'UnitPricePaid':price,'ProductPageURL':url})
            except Exception as e: self.order_process_log.append(f"  Error processing {mat_row.get('MaterialID','Unknown')}: {e}")
        if not items_to_order_by_supplier_id: self.order_process_log.append("No items to reorder."); return
        self.order_process_log.append("Populating proposed orders table..."); self.proposed_orders_table.setRowCount(0)
        for sup_id, items in items_to_order_by_supplier_id.items():
            sup_info_rows=current_suppliers_df[current_suppliers_df['SupplierID']==sup_id]
            if sup_info_rows.empty: self.order_process_log.append(f"  WARN: SupID '{sup_id}' not found for items: {[i['MaterialName'] for i in items]}."); continue
            sup_info=sup_info_rows.iloc[0]; sup_name=str(sup_info.get('SupplierName',sup_id)); method=str(sup_info.get('OrderMethod','N/A')).lower().strip()
            for item_dict in items:
                r=self.proposed_orders_table.rowCount(); self.proposed_orders_table.insertRow(r)
                col_idx_select = self.proposed_orders_cols.index("Select"); chkbox = QCheckBox(); self.proposed_orders_table.setCellWidget(r, col_idx_select, chkbox)
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("SupplierName"),QTableWidgetItem(sup_name))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("SupplierID"),QTableWidgetItem(sup_id))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("MaterialID"),QTableWidgetItem(item_dict['MaterialID']))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("MaterialName"),QTableWidgetItem(item_dict['MaterialName']))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("OrderQty"),QTableWidgetItem(str(item_dict['QuantityOrdered'])))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("Unit Price"),QTableWidgetItem(f"{item_dict['UnitPricePaid']:.2f}"))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("Total Price"),QTableWidgetItem(f"{(item_dict['QuantityOrdered']*item_dict['UnitPricePaid']):.2f}"))
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("OrderMethod"),QTableWidgetItem(method))
                action_str=""; url_btn_visible=False; url_to_open = ""
                if method=="email": action_str=f"Email: {sup_info.get('Email','N/A')}"
                elif method=="online":
                    item_url=item_dict['ProductPageURL']; sup_web=sup_info.get('SupplierWebsite','N/A'); url_to_open=item_url if item_url else sup_web
                    action_str=f"Online order at: {url_to_open if url_to_open else 'N/A'}"; url_btn_visible=bool(url_to_open)
                elif method=="phone": action_str=f"Phone: {sup_info.get('Phone','N/A')}"
                else: action_str="Manual Review"
                self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("ActionDetails"),QTableWidgetItem(action_str))
                if url_btn_visible:
                    btn=QPushButton("Open"); btn.clicked.connect(lambda chk=False, u=url_to_open: self.open_url_action(u))
                    self.proposed_orders_table.setCellWidget(r,self.proposed_orders_cols.index("Open Link"),btn)
                else: self.proposed_orders_table.setItem(r,self.proposed_orders_cols.index("Open Link"),QTableWidgetItem(""))
        self.proposed_orders_table.resizeColumnsToContents(); self.order_process_log.append("Order prep complete.")
        self.process_selected_orders_button.setEnabled(True if self.proposed_orders_table.rowCount() > 0 else False)

    def open_url_action(self, url_string):
        if not url_string: QMessageBox.information(self, "No URL", "No URL available."); return
        if not url_string.startswith(('http://','https://')): url_string='http://'+url_string
        if not QDesktopServices.openUrl(QUrl(url_string)): QMessageBox.warning(self,"Open URL Failed",f"Could not open: {url_string}")

    def process_selected_orders_action(self):
        self.order_process_log.append(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Processing selected orders...")
        selected_count = 0
        # This will be a list of dictionaries, each dict is a row from the table
        orders_to_log_and_action = []

        for r in range(self.proposed_orders_table.rowCount()):
            checkbox = self.proposed_orders_table.cellWidget(r, self.proposed_orders_cols.index("Select"))
            if checkbox and checkbox.isChecked():
                selected_count +=1
                # Extract all necessary data from the table row
                supplier_id = self.proposed_orders_table.item(r, self.proposed_orders_cols.index("SupplierID")).text()
                supplier_name = self.proposed_orders_table.item(r, self.proposed_orders_cols.index("SupplierName")).text()
                material_id = self.proposed_orders_table.item(r, self.proposed_orders_cols.index("MaterialID")).text()
                material_name = self.proposed_orders_table.item(r, self.proposed_orders_cols.index("MaterialName")).text()
                qty_ordered = get_float_val(self.proposed_orders_table.item(r, self.proposed_orders_cols.index("OrderQty")).text())
                unit_price = get_float_val(self.proposed_orders_table.item(r, self.proposed_orders_cols.index("Unit Price")).text())
                order_method = self.proposed_orders_table.item(r, self.proposed_orders_cols.index("OrderMethod")).text()
                # ProductPageURL for online orders is in ActionDetails or could be a hidden column
                # For simplicity, let's assume we might re-fetch it or it's part of ActionDetails if needed for action.

                orders_to_log_and_action.append({
                    "SupplierID": supplier_id, "SupplierName": supplier_name,
                    "MaterialID": material_id, "MaterialName": material_name,
                    "QuantityOrdered": qty_ordered, "UnitPricePaid": unit_price,
                    "OrderMethod": order_method,
                    # We might need to store the specific email or full URL from ActionDetails if it's complex
                    "ActionDetail": self.proposed_orders_table.item(r, self.proposed_orders_cols.index("ActionDetails")).text()
                })

        if not orders_to_log_and_action:
            self.order_process_log.append("No orders were selected to process."); return

        self.order_process_log.append(f"Found {len(orders_to_log_and_action)} selected order lines to process.")

        # Group by supplier for email generation
        grouped_for_email = {}
        new_history_entries = []

        # Generate OrderID per batch processed now, or per supplier later
        batch_order_id = generate_order_id() # One ID for this entire processing batch
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for order_detail in orders_to_log_and_action:
            supplier_id = order_detail["SupplierID"]
            # Log to history first
            history_entry = {
                'OrderID': batch_order_id, # Could also be more granular like per supplier
                'Timestamp': timestamp,
                'MaterialID': order_detail['MaterialID'],
                'MaterialName': order_detail['MaterialName'],
                'QuantityOrdered': order_detail['QuantityOrdered'],
                'UnitPricePaid': order_detail['UnitPricePaid'],
                'TotalPricePaid': order_detail['QuantityOrdered'] * order_detail['UnitPricePaid'],
                'SupplierID': supplier_id,
                'SupplierName': order_detail['SupplierName'],
                'OrderMethod': order_detail['OrderMethod'], # This is the method determined (e.g. "email")
                'Status': 'Ordered', # Initial status
                'Notes': 'Processed via GUI selection.'
            }
            new_history_entries.append(history_entry)

            if order_detail['OrderMethod'] == "email":
                grouped_for_email.setdefault(supplier_id, []).append({
                    'name': order_detail['MaterialName'],
                    'quantity': order_detail['QuantityOrdered']
                })
            elif order_detail['OrderMethod'] == "online":
                self.order_process_log.append(f"  CONFIRMED for online order: {order_detail['MaterialName']} from {order_detail['SupplierName']}. Details: {order_detail['ActionDetail']}")
            elif order_detail['OrderMethod'] == "phone":
                 self.order_process_log.append(f"  CONFIRMED for phone order: {order_detail['MaterialName']} from {order_detail['SupplierName']}. Details: {order_detail['ActionDetail']}")
            else: # Manual review
                 self.order_process_log.append(f"  CONFIRMED for manual review: {order_detail['MaterialName']} from {order_detail['SupplierName']}. Details: {order_detail['ActionDetail']}")


        # Send emails
        # Ensure action.py is imported: from action import generate_po_email_content, send_po_email
        from action import generate_po_email_content, send_po_email # Temporary import

        for supplier_id, items_for_email in grouped_for_email.items():
            supplier_info_rows = self.suppliers_df[self.suppliers_df['SupplierID'] == supplier_id]
            if not supplier_info_rows.empty:
                supplier_info = supplier_info_rows.iloc[0]
                supplier_name = str(supplier_info.get('SupplierName', supplier_id))
                supplier_email = str(supplier_info.get('Email','')).strip()
                if supplier_email:
                    self.order_process_log.append(f"  Generating email for {supplier_name} ({len(items_for_email)} items)...")
                    subject, body = generate_po_email_content(supplier_name, items_for_email)
                    if subject and body:
                        success = send_po_email(supplier_email, subject, body)
                        if success: self.order_process_log.append(f"    Email to {supplier_name} sent successfully.")
                        else: self.order_process_log.append(f"    FAILED to send email to {supplier_name}.")
                        # Update logged_method in history_entries for these items if needed
                        for entry in new_history_entries:
                            if entry['SupplierID'] == supplier_id and entry['OrderMethod'] == 'email':
                                entry['OrderMethod'] = "email_sent" if success else "email_failed_send"
                    else:
                        self.order_process_log.append(f"    FAILED to generate email content for {supplier_name}.")
                        for entry in new_history_entries:
                            if entry['SupplierID'] == supplier_id and entry['OrderMethod'] == 'email':
                                entry['OrderMethod'] = "email_failed_content"
                else:
                    self.order_process_log.append(f"  SKIPPED email for {supplier_name}: No email address found.")
                    for entry in new_history_entries:
                            if entry['SupplierID'] == supplier_id and entry['OrderMethod'] == 'email':
                                entry['OrderMethod'] = "email_failed_no_address"


        # Save all new history entries
        if new_history_entries:
            history_df_to_append = pd.DataFrame(new_history_entries)
            # Use self.save_any_dataframe to append and update self.order_history_df
            # This requires append_to_csv to be part of save_any_dataframe or a similar mechanism
            # For now, directly use our module-level append_to_csv
            append_to_csv(history_df_to_append, ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS)
            self.order_process_log.append(f"Logged {len(new_history_entries)} lines to {ORDER_HISTORY_FILE} with OrderID {batch_order_id}.")
            # Reload order history in the app
            self.order_history_df = load_or_create_dataframe_app(ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS, parent_widget=self, create_if_missing=True)


        self.order_process_log.append("Finished processing selected orders.")
        # Refresh the proposed orders table (it might now be empty or show fewer items)
        self.prepare_orders_action() # This will re-evaluate what needs ordering
        self.process_selected_orders_button.setEnabled(False if self.proposed_orders_table.rowCount() == 0 else True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_app_window = ProcurementAppGUI()
    main_app_window.show()
    sys.exit(app.exec())
