import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QLineEdit, QPushButton, QLabel, QFormLayout,
    QMessageBox, QComboBox, QSpinBox, QTextEdit, QHeaderView, QGroupBox # Added QGroupBox
)
from PyQt6.QtCore import Qt
import os

MATERIALS_FILE = "materials_master.csv"
SUPPLIERS_FILE = "suppliers.csv" # For future use

MATERIALS_HEADERS = ['MaterialID', 'MaterialName', 'Category', 'UnitOfMeasure',
                     'CurrentStock', 'ReorderPoint', 'StandardOrderQuantity',
                     'PreferredSupplierID', 'ProductPageURL', 'LeadTimeDays',
                     'SafetyStockQuantity', 'Notes']
SUPPLIERS_HEADERS = ['SupplierID', 'SupplierName', 'ContactPerson', 'Email',
                     'Phone', 'Website', 'OrderMethod']

class DataEntryHubGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Procurement Data Entry Hub")
        self.setGeometry(100, 100, 1000, 700)
        self.materials_df = self.load_or_create_dataframe(MATERIALS_FILE, MATERIALS_HEADERS)
        self.init_ui()
        self.refresh_materials_table()

    def load_or_create_dataframe(self, file_path, expected_headers):
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                df = pd.read_csv(file_path, dtype=str).fillna('')
                if not all(h in df.columns for h in expected_headers):
                    # Basic handling: if headers don't match, create fresh
                    df = pd.DataFrame(columns=expected_headers).astype(str).fillna('')
                    QMessageBox.warning(self, "File Warning", f"'{file_path}' headers incorrect. Loaded as empty. Save to create with correct schema.")
                return df
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Error loading {file_path}: {e}")
                return pd.DataFrame(columns=expected_headers).astype(str).fillna('')
        else:
            # Create empty df if file doesn't exist or is empty
            return pd.DataFrame(columns=expected_headers).astype(str).fillna('')

    def save_dataframe(self, df, file_path):
        try:
            df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Success", f"Data saved to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Error saving to {file_path}: {e}")

    def init_ui(self):
        self.tabs = QTabWidget(); self.setCentralWidget(self.tabs)
        self.materials_tab = QWidget(); self.tabs.addTab(self.materials_tab, "Materials Master")
        mat_layout = QVBoxLayout(self.materials_tab)
        self.materials_table_view = QTableWidget()
        self.materials_table_view.itemSelectionChanged.connect(self.on_material_selected)
        mat_layout.addWidget(self.materials_table_view)

        form_group = QGroupBox("Material Details"); form = QFormLayout()
        self.mat_id_edit = QLineEdit(); self.mat_name_edit = QLineEdit()
        self.mat_cat_edit = QLineEdit(); self.mat_uom_edit = QLineEdit()
        self.mat_stock_spin = QSpinBox(); self.mat_stock_spin.setRange(0,999999)
        self.mat_rop_spin = QSpinBox(); self.mat_rop_spin.setRange(0,999999)
        self.mat_soq_spin = QSpinBox(); self.mat_soq_spin.setRange(0,999999)
        self.mat_sup_id_edit = QLineEdit(); self.mat_url_edit = QLineEdit()
        self.mat_lead_spin = QSpinBox(); self.mat_lead_spin.setRange(0,365)
        self.mat_safe_stock_spin = QSpinBox(); self.mat_safe_stock_spin.setRange(0,999999)
        self.mat_notes_edit = QTextEdit(); self.mat_notes_edit.setFixedHeight(60)

        form.addRow("MaterialID*:", self.mat_id_edit); form.addRow("MaterialName*:", self.mat_name_edit)
        form.addRow("Category:", self.mat_cat_edit); form.addRow("Unit of Measure:", self.mat_uom_edit)
        form.addRow("Current Stock:", self.mat_stock_spin); form.addRow("Reorder Point:", self.mat_rop_spin)
        form.addRow("Std. Order Qty:", self.mat_soq_spin); form.addRow("Preferred SupplierID:", self.mat_sup_id_edit)
        form.addRow("Product Page URL:", self.mat_url_edit); form.addRow("Lead Time (Days):", self.mat_lead_spin)
        form.addRow("Safety Stock Qty:", self.mat_safe_stock_spin); form.addRow("Notes:", self.mat_notes_edit)
        form_group.setLayout(form); mat_layout.addWidget(form_group)

        btns = QHBoxLayout(); add=QPushButton("Add New"); save=QPushButton("Save"); del_btn=QPushButton("Delete"); clear=QPushButton("Clear Form")
        add.clicked.connect(self.add_new_material); save.clicked.connect(self.save_material)
        del_btn.clicked.connect(self.delete_material); clear.clicked.connect(self.clear_material_form)
        for btn_widget in [add, save, del_btn, clear]: btns.addWidget(btn_widget)
        mat_layout.addLayout(btns)

        self.suppliers_tab = QWidget(); self.tabs.addTab(self.suppliers_tab, "Suppliers (Coming Soon)")
        self.suppliers_tab.setLayout(QVBoxLayout()); self.suppliers_tab.layout().addWidget(QLabel("Supplier management here."))

    def refresh_materials_table(self):
        if self.materials_df is None: return
        self.materials_table_view.setRowCount(self.materials_df.shape[0])
        self.materials_table_view.setColumnCount(len(MATERIALS_HEADERS)) # Use defined headers
        self.materials_table_view.setHorizontalHeaderLabels(MATERIALS_HEADERS)
        for i in range(self.materials_df.shape[0]):
            for j, header in enumerate(MATERIALS_HEADERS):
                self.materials_table_view.setItem(i, j, QTableWidgetItem(str(self.materials_df.iloc[i].get(header, ''))))
        self.materials_table_view.resizeColumnsToContents()
        self.materials_table_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.materials_table_view.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

    def on_material_selected(self):
        rows = self.materials_table_view.selectionModel().selectedRows()
        if not rows: self.clear_material_form(); return
        data = self.materials_df.iloc[rows[0].row()]
        self.mat_id_edit.setText(str(data.get('MaterialID',''))); self.mat_id_edit.setReadOnly(True)
        self.mat_name_edit.setText(str(data.get('MaterialName','')))
        self.mat_cat_edit.setText(str(data.get('Category',''))); self.mat_uom_edit.setText(str(data.get('UnitOfMeasure','')))
        def get_int_val(val_str, default=0):
            try: return int(float(val_str)) if val_str else default
            except ValueError: return default
        self.mat_stock_spin.setValue(get_int_val(data.get('CurrentStock')))
        self.mat_rop_spin.setValue(get_int_val(data.get('ReorderPoint')))
        self.mat_soq_spin.setValue(get_int_val(data.get('StandardOrderQuantity')))
        self.mat_sup_id_edit.setText(str(data.get('PreferredSupplierID','')))
        self.mat_url_edit.setText(str(data.get('ProductPageURL','')))
        self.mat_lead_spin.setValue(get_int_val(data.get('LeadTimeDays')))
        self.mat_safe_stock_spin.setValue(get_int_val(data.get('SafetyStockQuantity')))
        self.mat_notes_edit.setText(str(data.get('Notes','')))

    def clear_material_form(self):
        self.mat_id_edit.clear(); self.mat_id_edit.setReadOnly(False); self.mat_id_edit.setPlaceholderText("Unique ID*")
        for editor in [self.mat_name_edit, self.mat_cat_edit, self.mat_uom_edit,
                       self.mat_sup_id_edit, self.mat_url_edit, self.mat_notes_edit]: editor.clear()
        for spinbox in [self.mat_stock_spin, self.mat_rop_spin, self.mat_soq_spin,
                        self.mat_lead_spin, self.mat_safe_stock_spin]: spinbox.setValue(0)
        self.materials_table_view.clearSelection()

    def add_new_material(self): self.clear_material_form(); self.mat_id_edit.setFocus()

    def save_material(self):
        mat_id = self.mat_id_edit.text().strip(); mat_name = self.mat_name_edit.text().strip()
        if not mat_id or not mat_name: QMessageBox.warning(self, "Input Error", "ID and Name required."); return

        data_dict = {h: "" for h in MATERIALS_HEADERS} # Ensure all headers exist
        data_dict.update({
            'MaterialID': mat_id, 'MaterialName': mat_name,
            'Category': self.mat_cat_edit.text().strip(), 'UnitOfMeasure': self.mat_uom_edit.text().strip(),
            'CurrentStock': str(self.mat_stock_spin.value()), 'ReorderPoint': str(self.mat_rop_spin.value()),
            'StandardOrderQuantity': str(self.mat_soq_spin.value()),
            'PreferredSupplierID': self.mat_sup_id_edit.text().strip(),
            'ProductPageURL': self.mat_url_edit.text().strip(),
            'LeadTimeDays': str(self.mat_lead_spin.value()),
            'SafetyStockQuantity': str(self.mat_safe_stock_spin.value()),
            'Notes': self.mat_notes_edit.toPlainText().strip()
        })

        existing_indices = self.materials_df.index[self.materials_df['MaterialID'] == mat_id].tolist()
        if existing_indices: # Update
            for k, v in data_dict.items(): self.materials_df.loc[existing_indices[0], k] = v
        else: # Add new
            new_row_df = pd.DataFrame([data_dict], columns=MATERIALS_HEADERS)
            self.materials_df = pd.concat([self.materials_df, new_row_df], ignore_index=True)

        self.save_dataframe(self.materials_df, MATERIALS_FILE)
        self.refresh_materials_table(); self.clear_material_form()

    def delete_material(self):
        rows = self.materials_table_view.selectionModel().selectedRows()
        if not rows: QMessageBox.warning(self, "Selection Error", "Select material to delete."); return
        mat_id_del = self.materials_df.iloc[rows[0].row()]['MaterialID']
        if QMessageBox.question(self, "Confirm", f"Delete '{mat_id_del}'?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.materials_df = self.materials_df[self.materials_df['MaterialID'] != mat_id_del]
            self.save_dataframe(self.materials_df, MATERIALS_FILE)
            self.refresh_materials_table(); self.clear_material_form()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = DataEntryHubGUI() # Or main_window = DataEntryHubGUI()
    win.show()
    sys.exit(app.exec())
