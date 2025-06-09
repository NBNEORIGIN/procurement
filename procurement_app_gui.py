import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QLineEdit, QPushButton, QLabel, QFormLayout,
    QMessageBox, QComboBox, QSpinBox, QTextEdit, QHeaderView, QDoubleSpinBox,
    QGroupBox, QCheckBox, QMenu # <--- QMenu ADDED, QCheckBox ADDED HERE
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIntValidator
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
                         'OrderMethod', 'Status', 'QuantityReceived', 'DateReceived', 'Notes']

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
        self._is_handling_item_change = False # Flag to prevent recursion for materials
        self._is_handling_supplier_item_change = False # Flag to prevent recursion for suppliers
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self); self.data_tabs = QTabWidget(); layout.addWidget(self.data_tabs)
        self.materials_tab_widget = QWidget(); self.data_tabs.addTab(self.materials_tab_widget, "Materials Master")
        mat_layout = QVBoxLayout(self.materials_tab_widget)
        self.materials_table_view = QTableWidget()
        self.materials_table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.materials_table_view.customContextMenuRequested.connect(self.show_materials_table_context_menu)
        self.materials_table_view.itemSelectionChanged.connect(self.on_material_selected)
        self.materials_table_view.itemChanged.connect(self.handle_material_item_changed) # Connect the itemChanged signal
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
        self.suppliers_table_view = QTableWidget()
        self.suppliers_table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.suppliers_table_view.customContextMenuRequested.connect(self.show_suppliers_table_context_menu)
        self.suppliers_table_view.itemSelectionChanged.connect(self.on_supplier_selected_from_table)
        self.suppliers_table_view.itemChanged.connect(self.handle_supplier_item_changed) # Connect itemChanged for suppliers
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
        self.materials_table_view.blockSignals(True)
        try:
            for header in MATERIALS_HEADERS:
                if header not in self.materials_df.columns: self.materials_df[header] = ''
            display_df = self.materials_df[MATERIALS_HEADERS].fillna('')
            self.materials_table_view.setRowCount(display_df.shape[0]); self.materials_table_view.setColumnCount(len(MATERIALS_HEADERS))
            self.materials_table_view.setHorizontalHeaderLabels(MATERIALS_HEADERS);self.materials_table_view.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            for i in range(display_df.shape[0]):
                for j, header in enumerate(MATERIALS_HEADERS):
                    item_value = str(display_df.iloc[i].get(header, ''))
                    table_item = QTableWidgetItem(item_value)
                    if header == 'MaterialID': # Make MaterialID column non-editable
                        table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.materials_table_view.setItem(i, j, table_item)
            self.materials_table_view.resizeColumnsToContents()
            self.materials_table_view.setEditTriggers(
                QTableWidget.EditTrigger.DoubleClicked |
                QTableWidget.EditTrigger.AnyKeyPressed |
                QTableWidget.EditTrigger.EditKeyPressed
            )
        finally:
            self.materials_table_view.blockSignals(False)

    def handle_material_item_changed(self, item):
        if self._is_handling_item_change:
            return # Prevent recursion

        self._is_handling_item_change = True
        try:
            row = item.row()
            col = item.column()
            new_value = item.text()
            header_name = MATERIALS_HEADERS[col]

            material_id_item = self.materials_table_view.item(row, MATERIALS_HEADERS.index('MaterialID'))
            if not material_id_item: # Should not happen if table is populated
                self._is_handling_item_change = False
                return

            material_id = material_id_item.text()

            if header_name == 'MaterialID' and new_value != material_id:
                # This case should ideally be prevented by setFlags, but as a fallback:
                QMessageBox.warning(self, "Edit Error", "MaterialID cannot be changed directly in the table.")
                # Revert the change in the GUI if possible, though setFlags should prevent this.
                # For simplicity, we assume setFlags works and this is a rare fallback.
                # item.setText(material_id) # This might trigger itemChanged again if not careful
                self._is_handling_item_change = False
                return

            # Find the index in the DataFrame
            df_idx = self.materials_df.index[self.materials_df['MaterialID'] == material_id].tolist()
            if not df_idx:
                QMessageBox.critical(self, "Update Error", f"Could not find MaterialID '{material_id}' in the DataFrame to update.")
                self._is_handling_item_change = False
                return # MaterialID not found, something is wrong

            # Update the DataFrame
            # Type conversion might be needed here depending on column data types
            # For now, assume string conversion is acceptable or underlying save handles it.
            self.materials_df.loc[df_idx[0], header_name] = new_value

            # Temporarily block signals during save to prevent itemChanged from firing due to programmatic updates
            # self.materials_table_view.blockSignals(True)
            self.parent_save_cb(MATERIALS_FILE, self.materials_df, MATERIALS_HEADERS)
            # self.materials_table_view.blockSignals(False)

            # Note: parent_save_cb might trigger a full refresh of the table.
            # If it does, the item objects might become invalid.
            # The _is_handling_item_change flag should still offer protection.
            # If parent_save_cb *also* updates the self.materials_df reference in this class
            # (e.g. self.materials_df = updated_df_from_parent_app), that's fine.

        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Error updating material item: {e}")
        finally:
            self._is_handling_item_change = False

    def on_material_selected(self):
        if self._is_handling_item_change: # Don't run selection logic if an edit is happening
            return
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
        self.suppliers_table_view.blockSignals(True)
        try:
            for header in SUPPLIERS_HEADERS:
                if header not in self.suppliers_df.columns: self.suppliers_df[header] = ''
            display_df = self.suppliers_df[SUPPLIERS_HEADERS].fillna('')
            self.suppliers_table_view.setRowCount(display_df.shape[0]); self.suppliers_table_view.setColumnCount(len(SUPPLIERS_HEADERS))
            self.suppliers_table_view.setHorizontalHeaderLabels(SUPPLIERS_HEADERS); self.suppliers_table_view.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            for i in range(display_df.shape[0]):
                for j, header in enumerate(SUPPLIERS_HEADERS):
                    item_value = str(display_df.iloc[i].get(header, ''))
                    table_item = QTableWidgetItem(item_value)
                    if header == 'SupplierID': # Make SupplierID column non-editable
                        table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.suppliers_table_view.setItem(i, j, table_item)
            self.suppliers_table_view.resizeColumnsToContents()
            self.suppliers_table_view.setEditTriggers(
                QTableWidget.EditTrigger.DoubleClicked |
                QTableWidget.EditTrigger.AnyKeyPressed |
                QTableWidget.EditTrigger.EditKeyPressed
            )
            # self.parent_refresh_sup_dd_cb() # This is called by parent app after this refresh is done via parent_save_cb
        finally:
            self.suppliers_table_view.blockSignals(False)

    def handle_supplier_item_changed(self, item):
        if self._is_handling_supplier_item_change:
            return # Prevent recursion

        self._is_handling_supplier_item_change = True
        try:
            row = item.row()
            col = item.column()
            new_value = item.text()
            header_name = SUPPLIERS_HEADERS[col]

            supplier_id_item = self.suppliers_table_view.item(row, SUPPLIERS_HEADERS.index('SupplierID'))
            if not supplier_id_item: # Should not happen
                self._is_handling_supplier_item_change = False
                return

            supplier_id = supplier_id_item.text()

            if header_name == 'SupplierID' and new_value != supplier_id:
                QMessageBox.warning(self, "Edit Error", "SupplierID cannot be changed directly in the table.")
                # item.setText(supplier_id) # Revert, but setFlags should prevent this
                self._is_handling_supplier_item_change = False
                return

            df_idx = self.suppliers_df.index[self.suppliers_df['SupplierID'] == supplier_id].tolist()
            if not df_idx:
                QMessageBox.critical(self, "Update Error", f"Could not find SupplierID '{supplier_id}' in DataFrame.")
                self._is_handling_supplier_item_change = False
                return

            self.suppliers_df.loc[df_idx[0], header_name] = new_value
            self.parent_save_cb(SUPPLIERS_FILE, self.suppliers_df, SUPPLIERS_HEADERS)
            # The parent_save_cb for suppliers already calls refresh for dropdowns in ProcurementAppGUI

        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Error updating supplier item: {e}")
        finally:
            self._is_handling_supplier_item_change = False

    def on_supplier_selected_from_table(self):
        if self._is_handling_supplier_item_change: # Don't run selection logic if an edit is happening
            return
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

    def show_materials_table_context_menu(self, position):
        menu = QMenu(self)
        add_above_action = menu.addAction("Add New Row Above")
        add_below_action = menu.addAction("Add New Row Below")
        delete_action = menu.addAction("Delete Selected Row(s)")

        action = menu.exec(self.materials_table_view.mapToGlobal(position))

        if action == add_above_action:
            self.add_material_row_above()
        elif action == add_below_action:
            self.add_material_row_below()
        elif action == delete_action:
            self.delete_selected_material_rows()

    def add_material_row_above(self):
        current_row = self.materials_table_view.currentRow()
        insert_idx = current_row if current_row != -1 else 0

        new_row_data = {col: '' for col in MATERIALS_HEADERS}
        # Potentially set a default unique ID or prompt user, for now, it's blank.
        # new_row_data['MaterialID'] = f"TEMP_ID_{datetime.now().strftime('%Y%m%d%H%M%S%f')}" # Example

        # Insert into DataFrame
        df_part1 = self.materials_df.iloc[:insert_idx]
        df_part2 = self.materials_df.iloc[insert_idx:]
        new_row_df = pd.DataFrame([new_row_data], columns=MATERIALS_HEADERS)

        self.materials_df = pd.concat([df_part1, new_row_df, df_part2]).reset_index(drop=True)

        self.parent_save_cb(MATERIALS_FILE, self.materials_df, MATERIALS_HEADERS)
        self.refresh_materials_table()
        # Optionally, select the new row:
        # self.materials_table_view.selectRow(insert_idx)

    def add_material_row_below(self):
        current_row = self.materials_table_view.currentRow()
        insert_idx = current_row + 1 if current_row != -1 else len(self.materials_df)

        new_row_data = {col: '' for col in MATERIALS_HEADERS}
        # new_row_data['MaterialID'] = f"TEMP_ID_{datetime.now().strftime('%Y%m%d%H%M%S%f')}" # Example

        df_part1 = self.materials_df.iloc[:insert_idx]
        df_part2 = self.materials_df.iloc[insert_idx:]
        new_row_df = pd.DataFrame([new_row_data], columns=MATERIALS_HEADERS)

        self.materials_df = pd.concat([df_part1, new_row_df, df_part2]).reset_index(drop=True)

        self.parent_save_cb(MATERIALS_FILE, self.materials_df, MATERIALS_HEADERS)
        self.refresh_materials_table()
        # Optionally, select the new row:
        # self.materials_table_view.selectRow(insert_idx)

    def delete_selected_material_rows(self):
        selected_model_indices = self.materials_table_view.selectionModel().selectedRows()
        if not selected_model_indices:
            QMessageBox.information(self, "No Selection", "Please select row(s) to delete.")
            return

        # Get unique MaterialIDs from selected rows in the view
        # Using column 0 for MaterialID as per MATERIALS_HEADERS
        material_id_col_idx = MATERIALS_HEADERS.index('MaterialID')
        material_ids_to_delete = []
        rows_to_delete_visual = sorted(list(set(index.row() for index in selected_model_indices)), reverse=True)

        for row_idx in rows_to_delete_visual:
            item = self.materials_table_view.item(row_idx, material_id_col_idx)
            if item and item.text():
                material_ids_to_delete.append(item.text())
            else:
                # This handles rows that might be blank or new (no MaterialID yet)
                # These will be removed by index from the dataframe if they don't have a MaterialID to match
                # However, the current logic relies on MaterialID matching.
                # For simplicity, we only delete rows that have a MaterialID.
                # A more robust solution might delete by DataFrame index if MaterialID is blank.
                QMessageBox.information(self, "Skipped Row", f"Skipped row {row_idx+1} as it has no MaterialID.")


        if not material_ids_to_delete:
             # This can happen if selected rows are new/blank and don't have MaterialIDs yet.
             # A simple approach is to delete based on visual row index if no material IDs were gathered.
             # For this iteration, we'll stick to MaterialID based deletion primarily.
            if rows_to_delete_visual: # If there were selected rows but no IDs (e.g. all blank)
                reply = QMessageBox.question(self, "Confirm Deletion",
                                         f"Delete {len(rows_to_delete_visual)} selected blank/new row(s)? "
                                         "These rows don't have MaterialIDs.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    # Create a list of indices to keep
                    indices_to_keep = [i for i in range(len(self.materials_df)) if i not in rows_to_delete_visual]
                    self.materials_df = self.materials_df.iloc[indices_to_keep].reset_index(drop=True)
                else:
                    return
            else: # No rows selected or no material IDs found
                QMessageBox.information(self, "No Action", "No rows with MaterialIDs selected for deletion.")
                return


        if material_ids_to_delete: # Only ask for confirmation if we have IDs
            reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete {len(material_ids_to_delete)} selected material(s)?\n"
                                     f"MaterialIDs: {', '.join(material_ids_to_delete)}",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
            # Proceed to delete rows from DataFrame that have these MaterialIDs
            self.materials_df = self.materials_df[~self.materials_df['MaterialID'].isin(material_ids_to_delete)].reset_index(drop=True)


        self.parent_save_cb(MATERIALS_FILE, self.materials_df, MATERIALS_HEADERS)
        self.refresh_materials_table()
        self.clear_material_form() # Clear form as a deleted item might have been shown

    def show_suppliers_table_context_menu(self, position):
        menu = QMenu(self)
        add_above_action = menu.addAction("Add New Row Above")
        add_below_action = menu.addAction("Add New Row Below")
        delete_action = menu.addAction("Delete Selected Row(s)")

        action = menu.exec(self.suppliers_table_view.mapToGlobal(position))

        if action == add_above_action:
            self.add_supplier_row_above()
        elif action == add_below_action:
            self.add_supplier_row_below()
        elif action == delete_action:
            self.delete_selected_supplier_rows()

    def add_supplier_row_above(self):
        current_row = self.suppliers_table_view.currentRow()
        insert_idx = current_row if current_row != -1 else 0

        new_row_data = {col: '' for col in SUPPLIERS_HEADERS}

        df_part1 = self.suppliers_df.iloc[:insert_idx]
        df_part2 = self.suppliers_df.iloc[insert_idx:]
        new_row_df = pd.DataFrame([new_row_data], columns=SUPPLIERS_HEADERS)

        self.suppliers_df = pd.concat([df_part1, new_row_df, df_part2]).reset_index(drop=True)

        self.parent_save_cb(SUPPLIERS_FILE, self.suppliers_df, SUPPLIERS_HEADERS)
        self.refresh_suppliers_table()
        # self.suppliers_table_view.selectRow(insert_idx)

    def add_supplier_row_below(self):
        current_row = self.suppliers_table_view.currentRow()
        insert_idx = current_row + 1 if current_row != -1 else len(self.suppliers_df)

        new_row_data = {col: '' for col in SUPPLIERS_HEADERS}

        df_part1 = self.suppliers_df.iloc[:insert_idx]
        df_part2 = self.suppliers_df.iloc[insert_idx:]
        new_row_df = pd.DataFrame([new_row_data], columns=SUPPLIERS_HEADERS)

        self.suppliers_df = pd.concat([df_part1, new_row_df, df_part2]).reset_index(drop=True)

        self.parent_save_cb(SUPPLIERS_FILE, self.suppliers_df, SUPPLIERS_HEADERS)
        self.refresh_suppliers_table()
        # self.suppliers_table_view.selectRow(insert_idx)

    def delete_selected_supplier_rows(self):
        selected_model_indices = self.suppliers_table_view.selectionModel().selectedRows()
        if not selected_model_indices:
            QMessageBox.information(self, "No Selection", "Please select supplier row(s) to delete.")
            return

        supplier_id_col_idx = SUPPLIERS_HEADERS.index('SupplierID')

        supplier_ids_to_delete_initially = []
        rows_to_delete_visual_indices = sorted(list(set(index.row() for index in selected_model_indices)), reverse=True)

        blank_rows_to_delete_indices = []

        for row_idx in rows_to_delete_visual_indices:
            item = self.suppliers_table_view.item(row_idx, supplier_id_col_idx)
            if item and item.text():
                supplier_ids_to_delete_initially.append(item.text())
            else:
                blank_rows_to_delete_indices.append(row_idx)

        suppliers_with_dependencies = {}
        final_supplier_ids_to_delete = []

        if not self.materials_df.empty and 'PreferredSupplierID' in self.materials_df.columns:
            for sup_id in supplier_ids_to_delete_initially:
                used_by_materials = self.materials_df[self.materials_df['PreferredSupplierID'] == sup_id]['MaterialID'].tolist()
                if used_by_materials:
                    suppliers_with_dependencies[sup_id] = used_by_materials
                else:
                    final_supplier_ids_to_delete.append(sup_id)
        else: # No materials data to check against
            final_supplier_ids_to_delete = list(supplier_ids_to_delete_initially)

        if suppliers_with_dependencies:
            error_messages = []
            for sup_id, mat_ids in suppliers_with_dependencies.items():
                error_messages.append(f"Supplier '{sup_id}' is preferred by MaterialIDs: {', '.join(mat_ids)}.")
            QMessageBox.warning(self, "Deletion Blocked", "Cannot delete supplier(s) due to dependencies:\n\n" + "\n".join(error_messages) + "\n\nPlease update materials first.")

        # Determine if any action can be taken
        can_delete_ids = len(final_supplier_ids_to_delete) > 0
        can_delete_blank_rows = len(blank_rows_to_delete_indices) > 0

        if not can_delete_ids and not can_delete_blank_rows:
            if not suppliers_with_dependencies : # Only show this if no other error was shown
                 QMessageBox.information(self, "No Action", "No suppliers can be deleted (either due to dependencies or no valid selection).")
            return

        confirm_messages = []
        if can_delete_ids:
            confirm_messages.append(f"{len(final_supplier_ids_to_delete)} supplier(s) with IDs: {', '.join(final_supplier_ids_to_delete)}.")
        if can_delete_blank_rows:
            confirm_messages.append(f"{len(blank_rows_to_delete_indices)} blank/new row(s).")

        reply = QMessageBox.question(self, "Confirm Deletion",
                                     "Are you sure you want to delete:\n" + "\n".join(confirm_messages),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        # Perform deletions
        deleted_something = False
        if can_delete_ids:
            self.suppliers_df = self.suppliers_df[~self.suppliers_df['SupplierID'].isin(final_supplier_ids_to_delete)].reset_index(drop=True)
            deleted_something = True

        if can_delete_blank_rows:
            # Adjust visual indices for DataFrame if IDs were also deleted
            # This is simpler if we just re-filter based on what's *not* in blank_rows_to_delete_indices
            # But since we sort reverse, direct iloc drop should be fine if done carefully.
            # For robustness, let's rebuild the DataFrame by keeping what's not deleted.
            current_df_indices_to_keep = []
            temp_df_for_blank_deletion = self.suppliers_df.copy() # Use current state of suppliers_df

            # Create a boolean mask for rows to keep
            keep_mask = pd.Series([True] * len(temp_df_for_blank_deletion))
            # Iterate through original visual indices marked for blank deletion
            # This part is tricky if other deletions happened.
            # A safer way for blank rows: if we decided to delete them, they were identified by visual index.
            # Re-fetch these rows' current indices in the potentially modified dataframe if some ID-based deletion happened.
            # However, the current logic processes ID-based deletions on self.suppliers_df first.
            # Then, blank row deletion should operate on the already modified self.suppliers_df.
            # The blank_rows_to_delete_indices are visual indices from the table *before* any deletion.
            # This logic needs to be careful.
            # Simplest: If blank rows were confirmed, and ID-based deletions happened,
            # it's hard to map old visual indices to new df indices.
            # The material table's blank deletion was simpler as it was the only deletion type if no IDs.
            # For now, let's assume if both ID and blank deletions are confirmed,
            # we handle ID deletion first, then re-evaluate blank row deletion based on remaining table state.
            # This is getting complex. Let's simplify: if blank rows are to be deleted, and ID rows are also deleted,
            # the blank row indices might shift.
            # Revisit blank row deletion strategy for combined cases later if issues arise.
            # For now, if blank_rows_to_delete_indices exist and were confirmed:
            # This assumes these indices are from the original table state.
            # This is NOT robust if combined with ID deletion.
            # A better way for blanks: just remove rows where SupplierID is empty if that's the criteria.
            # Let's stick to the visual index approach for now, acknowledging potential issues if mixed.
            if blank_rows_to_delete_indices and not can_delete_ids : # Only if no ID based deletion happened before.
                 indices_to_keep_for_blank = [i for i in range(len(self.suppliers_df)) if i not in blank_rows_to_delete_indices]
                 self.suppliers_df = self.suppliers_df.iloc[indices_to_keep_for_blank].reset_index(drop=True)
                 deleted_something = True
            elif blank_rows_to_delete_indices and can_delete_ids:
                 QMessageBox.information(self, "Note", "Deletion of blank rows in combination with ID-based deletion is complex and might be imprecise. Please verify.")
                 # Attempting to remove based on empty SupplierID after ID-based deletion
                 self.suppliers_df = self.suppliers_df[self.suppliers_df['SupplierID'] != ''].reset_index(drop=True)
                 deleted_something = True


        if deleted_something:
            self.parent_save_cb(SUPPLIERS_FILE, self.suppliers_df, SUPPLIERS_HEADERS)
            self.refresh_suppliers_table()
            self.clear_supplier_form()
            self.parent_refresh_sup_dd_cb() # Crucial for updating dropdowns

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
        self.proposed_orders_cols = ["Select", "SupplierName", "SupplierID", "MaterialID", "MaterialName", "OrderQty", "Unit Price", "Total Price", "OrderMethod", "ActionDetails"]
        self.proposed_orders_table.setColumnCount(len(self.proposed_orders_cols)); self.proposed_orders_table.setHorizontalHeaderLabels(self.proposed_orders_cols)
        self.proposed_orders_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); gen_ord_layout.addWidget(self.proposed_orders_table)
        self.order_process_log = QTextEdit(); self.order_process_log.setReadOnly(True); self.order_process_log.setFixedHeight(150)
        gen_ord_layout.addWidget(QLabel("Processing Log:")); gen_ord_layout.addWidget(self.order_process_log)
        
        # Order Check-In Tab
        self.order_checkin_tab = QWidget()
        checkin_layout = QVBoxLayout(self.order_checkin_tab)

        # Filter/Load Section
        filter_load_layout = QHBoxLayout()
        self.checkin_filter_label = QLabel("Filter by OrderID:")
        filter_load_layout.addWidget(self.checkin_filter_label)
        self.checkin_filter_edit = QLineEdit()
        self.checkin_filter_edit.setPlaceholderText("Enter OrderID to filter...")
        filter_load_layout.addWidget(self.checkin_filter_edit)
        self.checkin_load_button = QPushButton("Refresh / Load Orders")
        self.checkin_load_button.clicked.connect(self.load_checkable_orders) # Connect button
        filter_load_layout.addWidget(self.checkin_load_button)
        filter_load_layout.addStretch()
        checkin_layout.addLayout(filter_load_layout)

        # Orders Table Section
        self.checkin_orders_table = QTableWidget()
        self.checkin_orders_table_cols = ['Select', 'OrderID', 'MaterialID', 'MaterialName', 'QuantityOrdered', 'QuantityReceived', 'SupplierName', 'Status', 'OriginalIndex']
        self.checkin_orders_table.setColumnCount(len(self.checkin_orders_table_cols))
        self.checkin_orders_table.setHorizontalHeaderLabels(self.checkin_orders_table_cols)
        self.checkin_orders_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.checkin_orders_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # self.checkin_orders_table.itemSelectionChanged.connect(self.update_checkin_action_inputs_state) # Placeholder
        checkin_layout.addWidget(self.checkin_orders_table)

        # Action Inputs Section
        actions_form_layout = QFormLayout()
        self.checkin_qty_received_label = QLabel("Quantity Received:")
        self.checkin_qty_received_edit = QLineEdit()
        int_validator = QIntValidator()
        int_validator.setBottom(1) # Quantity must be positive
        self.checkin_qty_received_edit.setValidator(int_validator)
        actions_form_layout.addRow(self.checkin_qty_received_label, self.checkin_qty_received_edit)

        self.checkin_notes_label = QLabel("Notes (for issues/receiving):")
        self.checkin_notes_edit = QTextEdit()
        self.checkin_notes_edit.setFixedHeight(80)
        actions_form_layout.addRow(self.checkin_notes_label, self.checkin_notes_edit)
        checkin_layout.addLayout(actions_form_layout)

        # Action Buttons Section
        action_buttons_layout = QHBoxLayout()
        self.checkin_receive_full_button = QPushButton("Receive Selected as Full")
        self.checkin_receive_full_button.clicked.connect(self.receive_full_action) # Connect button
        action_buttons_layout.addWidget(self.checkin_receive_full_button)

        self.checkin_receive_partial_button = QPushButton("Receive Selected as Partial")
        self.checkin_receive_partial_button.clicked.connect(self.receive_partial_action) # Connect button
        action_buttons_layout.addWidget(self.checkin_receive_partial_button)

        self.checkin_flag_issue_button = QPushButton("Flag Issue with Selected")
        self.checkin_flag_issue_button.clicked.connect(self.flag_issue_action) # Connect button
        action_buttons_layout.addWidget(self.checkin_flag_issue_button)
        action_buttons_layout.addStretch()
        checkin_layout.addLayout(action_buttons_layout)

        self.update_checkin_action_buttons_state() # Set initial state

        # Log Area
        checkin_layout.addWidget(QLabel("Check-In Log:"))
        self.checkin_log_area = QTextEdit()
        self.checkin_log_area.setReadOnly(True)
        self.checkin_log_area.setFixedHeight(100)
        checkin_layout.addWidget(self.checkin_log_area)

        self.main_tabs.addTab(self.order_checkin_tab, "Order Check-In")
        
        self.data_management_widget.populate_preferred_supplier_dropdown()
        self.data_management_widget.refresh_materials_table(); self.data_management_widget.refresh_suppliers_table()
        self.load_checkable_orders() # Initial load

    def flag_issue_action(self):
        self.checkin_log_area.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Processing 'Flag Issue'...")

        selected_rows_indices = []
        for r in range(self.checkin_orders_table.rowCount()):
            checkbox = self.checkin_orders_table.cellWidget(r, self.checkin_orders_table_cols.index('Select'))
            if checkbox and checkbox.isChecked():
                selected_rows_indices.append(r)

        if len(selected_rows_indices) != 1:
            QMessageBox.warning(self, "Selection Error", "Please select exactly one order line to flag an issue.")
            self.checkin_log_area.append("Error: Exactly one line must be selected to flag an issue.")
            return

        selected_row_idx = selected_rows_indices[0]

        issue_notes = self.checkin_notes_edit.toPlainText().strip()
        if not issue_notes:
            QMessageBox.warning(self, "Input Error", "Please provide notes describing the issue in the 'Notes' field.")
            self.checkin_log_area.append("Error: Issue notes cannot be empty when flagging an issue.")
            return

        original_idx = -1 # Initialize for error messages
        try:
            original_idx_item = self.checkin_orders_table.item(selected_row_idx, self.checkin_orders_table_cols.index('OriginalIndex'))
            if original_idx_item is None or not original_idx_item.text():
                QMessageBox.critical(self, "Error", "Could not retrieve original order index from selected row for flagging issue.")
                self.checkin_log_area.append(f"Critical Error: Failed to retrieve OriginalIndex for flagging issue on table row {selected_row_idx}.")
                return
            original_idx = int(original_idx_item.text())

            if original_idx not in self.order_history_df.index:
                QMessageBox.critical(self, "Error", f"Original order index {original_idx} not found in history data for flagging issue.")
                self.checkin_log_area.append(f"Critical Error: OriginalIndex {original_idx} no longer valid for flagging issue.")
                return

            order_id_display = self.order_history_df.loc[original_idx, 'OrderID']
            material_name_display = self.order_history_df.loc[original_idx, 'MaterialName']
        except (AttributeError, ValueError, KeyError) as e:
            QMessageBox.critical(self, "Error", f"Could not retrieve order line details for flagging issue: {e}")
            self.checkin_log_area.append(f"Critical Error: Failed to retrieve details for selected line for flagging. OriginalIndex: {original_idx}. Error: {e}")
            return

        current_notes = str(self.order_history_df.loc[original_idx, 'Notes'])
        new_note_entry = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}-ISSUE]: {issue_notes}"

        self.order_history_df.loc[original_idx, 'Notes'] = (current_notes + new_note_entry).strip()
        self.order_history_df.loc[original_idx, 'Status'] = 'Issue Reported'

        self.save_any_dataframe(ORDER_HISTORY_FILE, self.order_history_df, ORDER_HISTORY_HEADERS)

        self.checkin_log_area.append(f"Issue flagged for OrderID {order_id_display}, Material {material_name_display}. Notes added. Status set to 'Issue Reported'.")

        self.load_checkable_orders()
        self.checkin_notes_edit.clear()
        self.checkin_qty_received_edit.clear() # Also clear qty field

    def receive_partial_action(self):
        self.checkin_log_area.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Processing 'Receive Partial'...")

        selected_rows_indices = []
        for r in range(self.checkin_orders_table.rowCount()):
            checkbox = self.checkin_orders_table.cellWidget(r, self.checkin_orders_table_cols.index('Select'))
            if checkbox and checkbox.isChecked():
                selected_rows_indices.append(r)

        if len(selected_rows_indices) != 1:
            QMessageBox.warning(self, "Selection Error", "Please select exactly one order line for partial receipt.")
            self.checkin_log_area.append("Error: Exactly one line must be selected for partial receipt.")
            return

        selected_row_idx = selected_rows_indices[0]

        try:
            qty_newly_received_str = self.checkin_qty_received_edit.text().strip()
            if not qty_newly_received_str: # Check if empty before attempting conversion
                QMessageBox.warning(self, "Input Error", "Quantity received cannot be empty.")
                self.checkin_log_area.append("Error: Quantity received input is empty.")
                return
            qty_newly_received = int(qty_newly_received_str) # Assuming integer quantities
            if qty_newly_received <= 0:
                QMessageBox.warning(self, "Input Error", "Quantity received must be a positive number.")
                self.checkin_log_area.append("Error: Quantity received must be positive.")
                return
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid quantity received. Please enter a whole number.")
            self.checkin_log_area.append("Error: Invalid quantity received format.")
            return

        original_idx = -1 # Initialize to ensure it's defined for error messages
        try:
            original_idx_item = self.checkin_orders_table.item(selected_row_idx, self.checkin_orders_table_cols.index('OriginalIndex'))
            if original_idx_item is None or not original_idx_item.text():
                 QMessageBox.critical(self, "Error", "Could not retrieve original order index from selected row.")
                 self.checkin_log_area.append(f"Critical Error: Failed to retrieve OriginalIndex for selected table row {selected_row_idx}.")
                 return
            original_idx = int(original_idx_item.text())

            if original_idx not in self.order_history_df.index:
                QMessageBox.critical(self, "Error", f"Original order index {original_idx} not found in history data.")
                self.checkin_log_area.append(f"Critical Error: OriginalIndex {original_idx} no longer valid.")
                return
            order_line = self.order_history_df.loc[original_idx].copy() # Use .copy() to avoid SettingWithCopyWarning
        except (AttributeError, ValueError, KeyError) as e:
            QMessageBox.critical(self, "Error", f"Could not retrieve order line details: {e}")
            self.checkin_log_area.append(f"Critical Error: Failed to retrieve details for selected line. OriginalIndex: {original_idx}. Error: {e}")
            return

        material_id = order_line['MaterialID']
        order_id_display = order_line['OrderID']
        material_name_display = order_line['MaterialName']

        qty_ordered_total = pd.to_numeric(order_line['QuantityOrdered'], errors='coerce').fillna(0)
        qty_already_received = pd.to_numeric(order_line.get('QuantityReceived', 0), errors='coerce').fillna(0)

        outstanding_qty = qty_ordered_total - qty_already_received

        if qty_newly_received > outstanding_qty:
            QMessageBox.warning(self, "Input Error", f"Quantity received ({qty_newly_received}) cannot exceed outstanding quantity ({outstanding_qty:.0f}).") # Format outstanding_qty
            self.checkin_log_area.append(f"Error: Received quantity {qty_newly_received} exceeds outstanding {outstanding_qty:.0f} for OrderID {order_id_display}, Material {material_name_display}.")
            return

        # Update self.order_history_df
        total_received_for_line = qty_already_received + qty_newly_received
        self.order_history_df.loc[original_idx, 'QuantityReceived'] = total_received_for_line
        self.order_history_df.loc[original_idx, 'DateReceived'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if total_received_for_line >= qty_ordered_total:
            self.order_history_df.loc[original_idx, 'Status'] = 'Received'
        else:
            self.order_history_df.loc[original_idx, 'Status'] = 'Partially Received'

        # Update self.materials_df
        material_rows = self.materials_df[self.materials_df['MaterialID'] == material_id]
        if not material_rows.empty:
            mat_idx = material_rows.index[0]
            current_stock = pd.to_numeric(self.materials_df.loc[mat_idx, 'CurrentStock'], errors='coerce').fillna(0)
            self.materials_df.loc[mat_idx, 'CurrentStock'] = current_stock + qty_newly_received
        else:
            self.checkin_log_area.append(f"Warning: MaterialID {material_id} not found in master for OrderID {order_id_display} during partial receipt stock update.")

        # Save DataFrames and Refresh
        self.save_any_dataframe(ORDER_HISTORY_FILE, self.order_history_df, ORDER_HISTORY_HEADERS)
        self.save_any_dataframe(MATERIALS_FILE, self.materials_df, MATERIALS_HEADERS)

        self.checkin_log_area.append(f"Partially received {qty_newly_received} for OrderID {order_id_display}, Material {material_name_display}. New total received: {total_received_for_line}. Data saved.")

        self.load_checkable_orders()
        if hasattr(self, 'data_management_widget'):
            self.data_management_widget.refresh_materials_table()

        self.checkin_qty_received_edit.clear()
        self.checkin_notes_edit.clear() # Also clear notes after processing

    def receive_full_action(self):
        self.checkin_log_area.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Processing 'Receive Full'...")
        processed_count = 0
        selected_rows_data = []

        for r in range(self.checkin_orders_table.rowCount()):
            checkbox = self.checkin_orders_table.cellWidget(r, self.checkin_orders_table_cols.index('Select'))
            if checkbox and checkbox.isChecked():
                try:
                    original_idx_item = self.checkin_orders_table.item(r, self.checkin_orders_table_cols.index('OriginalIndex'))
                    if original_idx_item is None or not original_idx_item.text():
                        self.checkin_log_area.append(f"  Skipping row {r} due to missing OriginalIndex.")
                        continue
                    original_idx = int(original_idx_item.text())

                    # Retrieve data directly from order_history_df
                    if original_idx not in self.order_history_df.index:
                        self.checkin_log_area.append(f"  Skipping row {r}: OriginalIndex {original_idx} not found in order_history_df.")
                        continue

                    order_line = self.order_history_df.loc[original_idx]
                    material_id = order_line['MaterialID']
                    qty_ordered = pd.to_numeric(order_line['QuantityOrdered'], errors='coerce')
                    if pd.isna(qty_ordered):
                        self.checkin_log_area.append(f"  Skipping row {r} (OrderID: {order_line['OrderID']}, Material: {order_line['MaterialName']}): Invalid QuantityOrdered.")
                        continue

                    selected_rows_data.append({
                        'original_idx': original_idx,
                        'material_id': material_id,
                        'qty_ordered': qty_ordered,
                        'order_id': order_line['OrderID'],
                        'material_name': order_line['MaterialName']
                    })
                except ValueError:
                    self.checkin_log_area.append(f"  Skipping row {r} due to invalid numeric data for OriginalIndex or QuantityOrdered.")
                    continue
                except Exception as e:
                    self.checkin_log_area.append(f"  Error processing selection for row {r}: {e}")
                    continue

        if not selected_rows_data:
            self.checkin_log_area.append("No items selected for full receipt.")
            return

        for item_data in selected_rows_data:
            original_idx = item_data['original_idx']
            material_id = item_data['material_id']
            qty_ordered = item_data['qty_ordered'] # Already numeric

            try:
                self.order_history_df.loc[original_idx, 'Status'] = 'Received'
                self.order_history_df.loc[original_idx, 'QuantityReceived'] = qty_ordered # Already numeric
                self.order_history_df.loc[original_idx, 'DateReceived'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                material_rows = self.materials_df[self.materials_df['MaterialID'] == material_id]
                if not material_rows.empty:
                    mat_idx = material_rows.index[0]
                    current_stock_val = self.materials_df.loc[mat_idx, 'CurrentStock']
                    current_stock = pd.to_numeric(current_stock_val, errors='coerce').fillna(0)
                    self.materials_df.loc[mat_idx, 'CurrentStock'] = current_stock + qty_ordered
                else:
                    self.checkin_log_area.append(f"Warning: MaterialID {material_id} not found in master for OrderID {item_data['order_id']}.")

                processed_count += 1
                self.checkin_log_area.append(f"  Fully received: OrderID {item_data['order_id']}, Material {item_data['material_name']}, Qty {qty_ordered}.")
            except Exception as e:
                self.checkin_log_area.append(f"  Error processing item OrderID {item_data['order_id']}, Material {item_data['material_name']}: {e}")


        if processed_count > 0:
            self.save_any_dataframe(ORDER_HISTORY_FILE, self.order_history_df, ORDER_HISTORY_HEADERS)
            self.save_any_dataframe(MATERIALS_FILE, self.materials_df, MATERIALS_HEADERS)
            self.checkin_log_area.append(f"Successfully processed {processed_count} lines for full receipt. Data saved.")
            self.load_checkable_orders()
            if hasattr(self, 'data_management_widget'):
                self.data_management_widget.refresh_materials_table()
        else:
            self.checkin_log_area.append("No items were ultimately processed for full receipt.")

    def load_checkable_orders(self):
        self.checkin_log_area.clear()
        self.checkin_log_area.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Loading checkable orders...")

        if self.order_history_df is None or self.order_history_df.empty:
            self.checkin_log_area.append("Order history is empty or not loaded.")
            self.checkin_orders_table.setRowCount(0)
            return

        relevant_orders_df = self.order_history_df[
            self.order_history_df['Status'].isin(['Ordered', 'Partially Received'])
        ].copy()

        filter_text = self.checkin_filter_edit.text().strip()
        if filter_text:
            relevant_orders_df = relevant_orders_df[relevant_orders_df['OrderID'].astype(str).str.contains(filter_text, case=False, na=False)]

        self.checkin_orders_table.setRowCount(0)

        # Ensure necessary columns exist in relevant_orders_df before iterating
        # This is more of a safeguard; they should exist from ORDER_HISTORY_HEADERS
        required_cols_for_display = ['OrderID', 'MaterialID', 'MaterialName', 'QuantityOrdered', 'QuantityReceived', 'SupplierName', 'Status']
        for col in required_cols_for_display:
            if col not in relevant_orders_df.columns:
                relevant_orders_df[col] = '' # Add missing columns with default empty string

        for index, order_data in relevant_orders_df.iterrows():
            r = self.checkin_orders_table.rowCount()
            self.checkin_orders_table.insertRow(r)

            # Select CheckBox
            chkbox = QCheckBox()
            chkbox.stateChanged.connect(self.update_checkin_action_buttons_state) # Connect state change
            self.checkin_orders_table.setCellWidget(r, self.checkin_orders_table_cols.index('Select'), chkbox)

            # Populate cells
            self.checkin_orders_table.setItem(r, self.checkin_orders_table_cols.index('OrderID'), QTableWidgetItem(str(order_data.get('OrderID', ''))))
            self.checkin_orders_table.setItem(r, self.checkin_orders_table_cols.index('MaterialID'), QTableWidgetItem(str(order_data.get('MaterialID', ''))))
            self.checkin_orders_table.setItem(r, self.checkin_orders_table_cols.index('MaterialName'), QTableWidgetItem(str(order_data.get('MaterialName', ''))))
            self.checkin_orders_table.setItem(r, self.checkin_orders_table_cols.index('QuantityOrdered'), QTableWidgetItem(str(order_data.get('QuantityOrdered', '0'))))
            self.checkin_orders_table.setItem(r, self.checkin_orders_table_cols.index('QuantityReceived'), QTableWidgetItem(str(order_data.get('QuantityReceived', '0'))))
            self.checkin_orders_table.setItem(r, self.checkin_orders_table_cols.index('SupplierName'), QTableWidgetItem(str(order_data.get('SupplierName', ''))))
            self.checkin_orders_table.setItem(r, self.checkin_orders_table_cols.index('Status'), QTableWidgetItem(str(order_data.get('Status', ''))))
            self.checkin_orders_table.setItem(r, self.checkin_orders_table_cols.index('OriginalIndex'), QTableWidgetItem(str(index)))

        self.checkin_orders_table.resizeColumnsToContents()
        self.checkin_log_area.append(f"Loaded {relevant_orders_df.shape[0]} order lines.")
        self.update_checkin_action_buttons_state() # Update button states after loading


    def update_checkin_action_buttons_state(self):
        selected_count = 0
        for r in range(self.checkin_orders_table.rowCount()):
            checkbox = self.checkin_orders_table.cellWidget(r, self.checkin_orders_table_cols.index('Select'))
            if checkbox and checkbox.isChecked():
                selected_count += 1

        self.checkin_receive_full_button.setEnabled(selected_count > 0)
        self.checkin_receive_partial_button.setEnabled(selected_count == 1)
        self.checkin_flag_issue_button.setEnabled(selected_count == 1)

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

                action_details_col_idx = self.proposed_orders_cols.index("ActionDetails")
                action_str = ""
                url_to_open = "" # Specific URL for the clickable link if applicable

                if method == "online":
                    item_page_url = item_dict['ProductPageURL']
                    supplier_website_url = sup_info.get('SupplierWebsite', 'N/A')
                    # Prioritize item-specific URL, fallback to supplier website
                    url_to_open = item_page_url if item_page_url else supplier_website_url
                    action_str = f"Online order at: {url_to_open if url_to_open else 'No URL available'}"
                elif method == "email":
                    action_str = f"Email: {sup_info.get('Email', 'N/A')}"
                elif method == "phone":
                    action_str = f"Phone: {sup_info.get('Phone', 'N/A')}"
                else: # Manual Review or other methods
                    action_str = "Manual Review"

                action_item = QTableWidgetItem()
                action_item.setData(Qt.ItemDataRole.UserRole, action_str) # Store raw string in UserRole
                self.proposed_orders_table.setItem(r, action_details_col_idx, action_item)

                if method == "online" and url_to_open and url_to_open != 'N/A':
                    parsed_url_to_open = url_to_open
                    if not parsed_url_to_open.startswith(('http://', 'https://')):
                        parsed_url_to_open = 'http://' + parsed_url_to_open

                    link_label = QLabel(f'<a href="{parsed_url_to_open}">{url_to_open}</a>')
                    link_label.setTextFormat(Qt.TextFormat.RichText)
                    link_label.setOpenExternalLinks(True)
                    self.proposed_orders_table.setCellWidget(r, action_details_col_idx, link_label)
                else:
                    action_item.setText(action_str) # Set display text if no widget overlay

        self.proposed_orders_table.resizeColumnsToContents(); self.order_process_log.append("Order prep complete.")
        self.process_selected_orders_button.setEnabled(True if self.proposed_orders_table.rowCount() > 0 else False)

    # open_url_action is no longer needed as QLabel with RichText handles opening links.
    # def open_url_action(self, url_string):
    #     if not url_string: QMessageBox.information(self, "No URL", "No URL available."); return
    #     if not url_string.startswith(('http://','https://')): url_string='http://'+url_string
    #     if not QDesktopServices.openUrl(QUrl(url_string)): QMessageBox.warning(self,"Open URL Failed",f"Could not open: {url_string}")

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
                    "ActionDetail": (item.data(Qt.ItemDataRole.UserRole) if (item := self.proposed_orders_table.item(r, self.proposed_orders_cols.index("ActionDetails"))) else "")
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
                'OrderMethod': order_detail['OrderMethod'], 'Status': 'Ordered',
                'QuantityReceived': 0, 'DateReceived': '', 'Notes': 'Processed via GUI selection.'
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
