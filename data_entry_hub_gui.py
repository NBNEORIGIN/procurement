import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QLineEdit, QPushButton, QLabel, QFormLayout,
    QMessageBox, QComboBox, QSpinBox, QTextEdit, QHeaderView, QDoubleSpinBox,
    QGroupBox
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
import os

MATERIALS_FILE = "materials_master.csv"
SUPPLIERS_FILE = "suppliers.csv"

MATERIALS_HEADERS = ['MaterialID', 'MaterialName', 'Category', 'UnitOfMeasure', 'CurrentStock',
                     'ReorderPoint', 'StandardOrderQuantity', 'PreferredSupplierID',
                     'ProductPageURL', 'LeadTimeDays', 'SafetyStockQuantity', 'Notes', 'CurrentPrice']
SUPPLIERS_HEADERS = ['SupplierID', 'SupplierName', 'ContactPerson', 'Email', 'Phone', 'Website', 'OrderMethod']

def get_int_val(val_str, default=0):
    try: return int(float(str(val_str))) if pd.notna(val_str) and str(val_str).strip() != '' else default
    except ValueError: return default
def get_float_val(val_str, default=0.0):
    try: return float(str(val_str)) if pd.notna(val_str) and str(val_str).strip() != '' else default
    except ValueError: return default

class DataEntryHubGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Procurement Data Entry Hub"); self.setGeometry(100, 100, 1100, 800)
        self.materials_df = self.load_or_create_dataframe(MATERIALS_FILE, MATERIALS_HEADERS)
        self.suppliers_df = self.load_or_create_dataframe(SUPPLIERS_FILE, SUPPLIERS_HEADERS)
        self.init_ui()
        self.refresh_materials_table(); self.refresh_suppliers_table()

    def load_or_create_dataframe(self, file_path, expected_headers):
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                df = pd.read_csv(file_path, dtype=str).fillna('')
                for header in expected_headers:
                    if header not in df.columns: df[header] = ''
                return df[expected_headers].fillna('')
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Error loading {file_path}: {e}")
                return pd.DataFrame(columns=expected_headers).astype(str).fillna('')
        return pd.DataFrame(columns=expected_headers).astype(str).fillna('')

    def save_dataframe(self, df, file_path, headers_order):
        try:
            df_to_save = df.copy()
            for header in headers_order:
                 if header not in df_to_save.columns: df_to_save[header] = ''
            df_to_save[headers_order].to_csv(file_path, index=False)
            QMessageBox.information(self, "Success", f"Data saved to {file_path}")
        except Exception as e: QMessageBox.critical(self, "Save Error", f"Error saving to {file_path}: {e}")

    def init_ui(self):
        self.tabs = QTabWidget(); self.setCentralWidget(self.tabs)
        self.materials_tab = QWidget(); self.tabs.addTab(self.materials_tab, "Materials Master")
        mat_layout = QVBoxLayout(self.materials_tab)
        self.materials_table_view = QTableWidget()
        self.materials_table_view.itemSelectionChanged.connect(self.on_material_selected)
        mat_layout.addWidget(self.materials_table_view)
        mat_form_group = QGroupBox("Material Details"); mat_form = QFormLayout()
        self.mat_id_edit = QLineEdit(); self.mat_name_edit = QLineEdit(); self.mat_cat_edit = QLineEdit(); self.mat_uom_edit = QLineEdit()
        self.mat_stock_spin = QSpinBox(); self.mat_stock_spin.setRange(0,999999)
        self.mat_rop_spin = QSpinBox(); self.mat_rop_spin.setRange(0,999999)
        self.mat_soq_spin = QSpinBox(); self.mat_soq_spin.setRange(0,999999)
        self.mat_price_spin = QDoubleSpinBox(); self.mat_price_spin.setRange(0,99999.99); self.mat_price_spin.setDecimals(2); self.mat_price_spin.setPrefix("£")
        self.mat_pref_sup_combo = QComboBox()
        self.mat_url_edit = QLineEdit(); self.mat_url_open_btn = QPushButton("Open Link"); self.mat_url_open_btn.clicked.connect(self.open_material_url)
        mat_url_layout = QHBoxLayout(); mat_url_layout.addWidget(self.mat_url_edit); mat_url_layout.addWidget(self.mat_url_open_btn)
        self.mat_lead_spin = QSpinBox(); self.mat_lead_spin.setRange(0,365)
        self.mat_safe_stock_spin = QSpinBox(); self.mat_safe_stock_spin.setRange(0,999999)
        self.mat_notes_edit = QTextEdit(); self.mat_notes_edit.setFixedHeight(60)
        mat_form.addRow("MaterialID*:", self.mat_id_edit); mat_form.addRow("MaterialName*:", self.mat_name_edit)
        mat_form.addRow("Category:", self.mat_cat_edit); mat_form.addRow("Unit of Measure:", self.mat_uom_edit)
        mat_form.addRow("Current Stock:", self.mat_stock_spin); mat_form.addRow("Reorder Point:", self.mat_rop_spin)
        mat_form.addRow("Std. Order Qty:", self.mat_soq_spin); mat_form.addRow("Current Price:", self.mat_price_spin)
        mat_form.addRow("Preferred SupplierID:", self.mat_pref_sup_combo)
        mat_form.addRow("Product Page URL:", mat_url_layout)
        mat_form.addRow("Lead Time (Days):", self.mat_lead_spin)
        mat_form.addRow("Safety Stock Qty:", self.mat_safe_stock_spin); mat_form.addRow("Notes:", self.mat_notes_edit)
        mat_form_group.setLayout(mat_form); mat_layout.addWidget(mat_form_group)
        mat_btns = QHBoxLayout(); mat_add=QPushButton("Add New"); mat_save=QPushButton("Save"); mat_del=QPushButton("Delete"); mat_clear=QPushButton("Clear Form")
        mat_add.clicked.connect(self.add_new_material); mat_save.clicked.connect(self.save_material)
        mat_del.clicked.connect(self.delete_material); mat_clear.clicked.connect(self.clear_material_form)
        for btn in [mat_add, mat_save, mat_del, mat_clear]: mat_btns.addWidget(btn)
        mat_layout.addLayout(mat_btns)

        self.suppliers_tab = QWidget(); self.tabs.addTab(self.suppliers_tab, "Suppliers")
        sup_layout = QVBoxLayout(self.suppliers_tab)
        self.suppliers_table_view = QTableWidget(); self.suppliers_table_view.itemSelectionChanged.connect(self.on_supplier_selected_from_table)
        sup_layout.addWidget(self.suppliers_table_view)
        sup_form_group = QGroupBox("Supplier Details"); sup_form_details = QFormLayout()
        self.sup_id_edit = QLineEdit(); self.sup_name_edit = QLineEdit(); self.sup_contact_edit = QLineEdit()
        self.sup_email_edit = QLineEdit(); self.sup_phone_edit = QLineEdit()
        self.sup_website_edit = QLineEdit(); self.sup_website_open_btn = QPushButton("Open Link"); self.sup_website_open_btn.clicked.connect(self.open_supplier_website)
        sup_website_layout = QHBoxLayout(); sup_website_layout.addWidget(self.sup_website_edit); sup_website_layout.addWidget(self.sup_website_open_btn)
        self.sup_order_method_combo = QComboBox(); self.sup_order_method_combo.addItems(["", "email", "online", "phone", "other"])
        sup_form_details.addRow("SupplierID*:", self.sup_id_edit); sup_form_details.addRow("SupplierName*:", self.sup_name_edit)
        sup_form_details.addRow("Contact Person:", self.sup_contact_edit); sup_form_details.addRow("Email:", self.sup_email_edit)
        sup_form_details.addRow("Phone:", self.sup_phone_edit); sup_form_details.addRow("Website:", sup_website_layout)
        sup_form_details.addRow("Order Method:", self.sup_order_method_combo)
        sup_form_group.setLayout(sup_form_details); sup_layout.addWidget(sup_form_group)
        sup_btns = QHBoxLayout(); sup_add=QPushButton("Add New"); sup_save=QPushButton("Save"); sup_del=QPushButton("Delete"); sup_clear=QPushButton("Clear Form")
        sup_add.clicked.connect(self.add_new_supplier); sup_save.clicked.connect(self.save_supplier)
        sup_del.clicked.connect(self.delete_supplier); sup_clear.clicked.connect(self.clear_supplier_form)
        for btn in [sup_add, sup_save, sup_del, sup_clear]: sup_btns.addWidget(btn)
        sup_layout.addLayout(sup_btns)
        self.populate_preferred_supplier_dropdown()

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
        if not self.suppliers_df.empty and 'SupplierID' in self.suppliers_df.columns and 'SupplierName' in self.suppliers_df.columns:
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
        self.materials_table_view.setHorizontalHeaderLabels(MATERIALS_HEADERS)
        for i in range(display_df.shape[0]):
            for j, header in enumerate(MATERIALS_HEADERS):
                self.materials_table_view.setItem(i, j, QTableWidgetItem(str(display_df.iloc[i].get(header, ''))))
        self.materials_table_view.resizeColumnsToContents(); self.materials_table_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.materials_table_view.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

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

        material_id = mat_id_item.text()

        data_rows = self.materials_df[self.materials_df['MaterialID'] == material_id]

        if data_rows.empty:
            self.clear_material_form()
            # Optional: QMessageBox.warning(self, "Data Sync Error", f"MaterialID '{material_id}' not found in DataFrame.")
            return  # Explicitly return if no data found

        # This line is now only reached if data_rows is NOT empty
        data = data_rows.iloc[0]

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
        for editor in [self.mat_name_edit, self.mat_cat_edit, self.mat_uom_edit, self.mat_url_edit, self.mat_notes_edit]: editor.clear()
        for spinbox in [self.mat_stock_spin,self.mat_rop_spin,self.mat_soq_spin,self.mat_lead_spin,self.mat_safe_stock_spin]: spinbox.setValue(0)
        self.mat_price_spin.setValue(0.0); self.mat_pref_sup_combo.setCurrentIndex(0)
        self.materials_table_view.clearSelection()

    def add_new_material(self): self.clear_material_form(); self.mat_id_edit.setFocus()

    def save_material(self):
        mat_id = self.mat_id_edit.text().strip(); mat_name = self.mat_name_edit.text().strip()
        if not mat_id or not mat_name: QMessageBox.warning(self, "Input Error", "ID and Name required."); return
        pref_sup_id_val = self.mat_pref_sup_combo.currentData(); pref_sup_id_val = "" if pref_sup_id_val is None else pref_sup_id_val
        data_dict = {h: "" for h in MATERIALS_HEADERS}
        data_dict.update({
            'MaterialID': mat_id, 'MaterialName': mat_name,
            'Category': self.mat_cat_edit.text().strip(), 'UnitOfMeasure': self.mat_uom_edit.text().strip(),
            'CurrentStock': str(self.mat_stock_spin.value()), 'ReorderPoint': str(self.mat_rop_spin.value()),
            'StandardOrderQuantity': str(self.mat_soq_spin.value()), 'CurrentPrice': "%.2f" % self.mat_price_spin.value(),
            'PreferredSupplierID': pref_sup_id_val,
            'ProductPageURL': self.mat_url_edit.text().strip(),
            'LeadTimeDays': str(self.mat_lead_spin.value()),
            'SafetyStockQuantity': str(self.mat_safe_stock_spin.value()),
            'Notes': self.mat_notes_edit.toPlainText().strip()
        })
        existing = self.materials_df.index[self.materials_df['MaterialID'] == mat_id].tolist()
        if existing: self.materials_df.loc[existing[0]] = pd.Series(data_dict)
        else: self.materials_df = pd.concat([self.materials_df, pd.DataFrame([data_dict], columns=MATERIALS_HEADERS)], ignore_index=True)
        self.save_dataframe(self.materials_df, MATERIALS_FILE, MATERIALS_HEADERS)
        self.refresh_materials_table(); self.clear_material_form()

    def delete_material(self):
        rows = self.materials_table_view.selectionModel().selectedRows()
        if not rows: QMessageBox.warning(self, "Selection Error", "Select material to delete."); return
        idx = MATERIALS_HEADERS.index('MaterialID')
        mat_id_del = self.materials_table_view.item(rows[0].row(), idx).text()
        if QMessageBox.question(self, "Confirm", f"Delete '{mat_id_del}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.materials_df = self.materials_df[self.materials_df['MaterialID'] != mat_id_del].reset_index(drop=True)
            self.save_dataframe(self.materials_df, MATERIALS_FILE, MATERIALS_HEADERS)
            self.refresh_materials_table(); self.clear_material_form()

    def refresh_suppliers_table(self):
        if self.suppliers_df is None: return
        for header in SUPPLIERS_HEADERS:
            if header not in self.suppliers_df.columns: self.suppliers_df[header] = ''
        display_df = self.suppliers_df[SUPPLIERS_HEADERS].fillna('')
        self.suppliers_table_view.setRowCount(display_df.shape[0]); self.suppliers_table_view.setColumnCount(len(SUPPLIERS_HEADERS))
        self.suppliers_table_view.setHorizontalHeaderLabels(SUPPLIERS_HEADERS)
        for i in range(display_df.shape[0]):
            for j, header in enumerate(SUPPLIERS_HEADERS):
                self.suppliers_table_view.setItem(i, j, QTableWidgetItem(str(display_df.iloc[i].get(header, ''))))
        self.suppliers_table_view.resizeColumnsToContents(); self.suppliers_table_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.suppliers_table_view.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.populate_preferred_supplier_dropdown()

    def on_supplier_selected_from_table(self): # CORRECTED METHOD
        rows = self.suppliers_table_view.selectionModel().selectedRows()
        if not rows:
            self.clear_supplier_form()
            return

        selected_row_index_in_view = rows[0].row()

        supplier_id_col_idx = SUPPLIERS_HEADERS.index('SupplierID')
        sup_id_item = self.suppliers_table_view.item(selected_row_index_in_view, supplier_id_col_idx)

        if not sup_id_item or not sup_id_item.text():
            self.clear_supplier_form()
            return

        supplier_id = sup_id_item.text() # Defined variable `supplier_id`

        data_rows = self.suppliers_df[self.suppliers_df['SupplierID'] == supplier_id] # Used corrected `supplier_id`

        if data_rows.empty:
            self.clear_supplier_form()
            return

        data = data_rows.iloc[0]

        self.sup_id_edit.setText(str(data.get('SupplierID', ''))); self.sup_id_edit.setReadOnly(True)
        self.sup_name_edit.setText(str(data.get('SupplierName', '')))
        self.sup_contact_edit.setText(str(data.get('ContactPerson', '')))
        self.sup_email_edit.setText(str(data.get('Email', '')))
        self.sup_phone_edit.setText(str(data.get('Phone', '')))
        self.sup_website_edit.setText(str(data.get('Website', '')))
        self.sup_order_method_combo.setCurrentText(str(data.get('OrderMethod', '')))

    def clear_supplier_form(self):
        self.sup_id_edit.clear(); self.sup_id_edit.setReadOnly(False); self.sup_id_edit.setPlaceholderText("Unique ID*")
        for editor in [self.sup_name_edit, self.sup_contact_edit, self.sup_email_edit, self.sup_phone_edit, self.sup_website_edit]: editor.clear()
        self.sup_order_method_combo.setCurrentIndex(0)
        self.suppliers_table_view.clearSelection()

    def add_new_supplier(self): self.clear_supplier_form(); self.sup_id_edit.setFocus()

    def save_supplier(self):
        sup_id = self.sup_id_edit.text().strip(); sup_name = self.sup_name_edit.text().strip()
        if not sup_id or not sup_name: QMessageBox.warning(self, "Input Error", "SupplierID and Name required."); return
        data_dict = {h: "" for h in SUPPLIERS_HEADERS}
        data_dict.update({
            'SupplierID': sup_id, 'SupplierName': sup_name,
            'ContactPerson': self.sup_contact_edit.text().strip(), 'Email': self.sup_email_edit.text().strip(),
            'Phone': self.sup_phone_edit.text().strip(), 'Website': self.sup_website_edit.text().strip(),
            'OrderMethod': self.sup_order_method_combo.currentText()
        })
        existing = self.suppliers_df.index[self.suppliers_df['SupplierID'] == sup_id].tolist()
        if existing: self.suppliers_df.loc[existing[0]] = pd.Series(data_dict)
        else: self.suppliers_df = pd.concat([self.suppliers_df, pd.DataFrame([data_dict], columns=SUPPLIERS_HEADERS)], ignore_index=True)
        self.save_dataframe(self.suppliers_df, SUPPLIERS_FILE, SUPPLIERS_HEADERS)
        self.refresh_suppliers_table(); self.clear_supplier_form()

    def delete_supplier(self):
        rows = self.suppliers_table_view.selectionModel().selectedRows()
        if not rows: QMessageBox.warning(self, "Selection Error", "Select supplier to delete."); return
        idx = SUPPLIERS_HEADERS.index('SupplierID')
        sup_id_del = self.suppliers_table_view.item(rows[0].row(), idx).text()
        if not self.materials_df.empty and 'PreferredSupplierID' in self.materials_df.columns:
            used_by = self.materials_df[self.materials_df['PreferredSupplierID'] == sup_id_del]['MaterialID'].tolist()
            if used_by:
                QMessageBox.warning(self, "Deletion Error", f"Supplier '{sup_id_del}' used by materials: {', '.join(used_by)}. Update them first.")
                return
        if QMessageBox.question(self, "Confirm", f"Delete '{sup_id_del}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.suppliers_df = self.suppliers_df[self.suppliers_df['SupplierID'] != sup_id_del].reset_index(drop=True)
            self.save_dataframe(self.suppliers_df, SUPPLIERS_FILE, SUPPLIERS_HEADERS)
            self.refresh_suppliers_table(); self.clear_supplier_form()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = DataEntryHubGUI()
    win.show()
    sys.exit(app.exec())
