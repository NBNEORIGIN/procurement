import sys
import json
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLineEdit, QPushButton, QLabel, QFormLayout,
    QMessageBox, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox
)
from PyQt6.QtCore import Qt

SUPPLIERS_FILE = "suppliers.json"
INVENTORY_FILE = "current_inventory.csv"
RULES_FILE = "procurement_rules.json"

# --- Data Loading Helper Functions ---
def load_json_file(file_path, default_type={}):
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except FileNotFoundError: return default_type # No pop-up here for cleaner startup
    except json.JSONDecodeError: return default_type

def load_csv_to_df(file_path):
    try: return pd.read_csv(file_path)
    except FileNotFoundError: return pd.DataFrame()
    except Exception as e: return pd.DataFrame()

class CentralHubGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Procurement Data Hub")
        self.setGeometry(100, 100, 900, 700)

        self.suppliers_data = load_json_file(SUPPLIERS_FILE)
        self.inventory_df = load_csv_to_df(INVENTORY_FILE)
        self.rules_data_list = load_json_file(RULES_FILE, default_type=[])
        
        self.rules_map = {rule.get('RawMaterial', ''): rule for rule in self.rules_data_list}
        if not self.inventory_df.empty and 'RawMaterial' in self.inventory_df.columns:
            self.inventory_map = self.inventory_df.set_index('RawMaterial')['CurrentStock'].to_dict()
        else: self.inventory_map = {}

        self.current_selected_supplier_key = None
        self.init_ui()
        self.populate_supplier_list()
        self.clear_all_fields()
        
        # Show initial file loading status (optional)
        if not self.suppliers_data: QMessageBox.warning(self, "File Load Warning", f"{SUPPLIERS_FILE} not found or invalid.")
        if self.inventory_df.empty: QMessageBox.warning(self, "File Load Warning", f"{INVENTORY_FILE} not found or invalid.")
        if not self.rules_data_list: QMessageBox.warning(self, "File Load Warning", f"{RULES_FILE} not found or invalid.")


    def init_ui(self):
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        left_panel = QVBoxLayout(); left_panel.addWidget(QLabel("Suppliers:"))
        self.supplier_list_widget = QListWidget(); self.supplier_list_widget.itemClicked.connect(self.on_supplier_selected)
        left_panel.addWidget(self.supplier_list_widget); main_layout.addLayout(left_panel, 1)

        right_panel = QVBoxLayout()
        
        sup_group = QGroupBox("Supplier Details"); sup_form = QFormLayout()
        self.name_edit = QLineEdit(); self.name_edit.setReadOnly(True)
        self.web_edit = QLineEdit(); self.mail_edit = QLineEdit(); self.contact_edit = QLineEdit(); self.phone_edit = QLineEdit()
        self.method_combo = QComboBox(); self.method_combo.addItems(["", "email", "online", "phone", "other"])
        self.order_web_edit = QLineEdit()
        sup_form.addRow("Name:", self.name_edit); sup_form.addRow("Website:", self.web_edit); sup_form.addRow("Email:", self.mail_edit)
        sup_form.addRow("Contact:", self.contact_edit); sup_form.addRow("Phone:", self.phone_edit)
        sup_form.addRow("Order Method:", self.method_combo); sup_form.addRow("Order Website:", self.order_web_edit)
        sup_group.setLayout(sup_form); right_panel.addWidget(sup_group)

        mat_group = QGroupBox("Materials Supplied & Inventory (View Only This Version)"); mat_layout = QVBoxLayout()
        self.materials_table = QTableWidget(); self.materials_table.setColumnCount(4)
        self.materials_table.setHorizontalHeaderLabels(["Material", "Stock", "ROP", "Std. Order Qty"])
        self.materials_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        mat_layout.addWidget(self.materials_table)
        # Placeholder buttons for linking/unlinking materials - functionality later
        link_btns = QHBoxLayout(); add_mat_btn = QPushButton("Link Material"); rem_mat_btn = QPushButton("Unlink Material")
        link_btns.addWidget(add_mat_btn); link_btns.addWidget(rem_mat_btn); mat_layout.addLayout(link_btns)
        mat_group.setLayout(mat_layout); right_panel.addWidget(mat_group)
        
        action_btns = QHBoxLayout(); add_sup_btn = QPushButton("Add Supplier"); save_btn = QPushButton("Save All (Disabled)"); del_sup_btn = QPushButton("Delete Supplier")
        save_btn.setEnabled(False) # Disabled for this version
        action_btns.addWidget(add_sup_btn); action_btns.addWidget(save_btn); action_btns.addWidget(del_sup_btn)
        right_panel.addLayout(action_btns)
        main_layout.addLayout(right_panel, 3)

    def populate_supplier_list(self):
        self.supplier_list_widget.clear()
        if self.suppliers_data:
            for name in sorted(self.suppliers_data.keys()): self.supplier_list_widget.addItem(name)

    def on_supplier_selected(self, item):
        self.current_selected_supplier_key = item.text()
        details = self.suppliers_data.get(self.current_selected_supplier_key, {})
        self.name_edit.setText(self.current_selected_supplier_key)
        self.web_edit.setText(details.get("website", "")); self.mail_edit.setText(details.get("email", ""))
        self.contact_edit.setText(details.get("contact_person", "")); self.phone_edit.setText(details.get("phone", ""))
        om = details.get("order_method", ""); self.method_combo.setCurrentText(om) if om else self.method_combo.setCurrentIndex(0)
        self.order_web_edit.setText(details.get("supplier_website", ""))
        self.populate_materials_table(details.get("materials_supplied", []))

    def populate_materials_table(self, material_names):
        self.materials_table.setRowCount(0)
        if not material_names: return
        self.materials_table.setRowCount(len(material_names))
        for r, name in enumerate(material_names):
            name_item = QTableWidgetItem(name); name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.materials_table.setItem(r, 0, name_item)
            self.materials_table.setItem(r, 1, QTableWidgetItem(str(self.inventory_map.get(name, ""))))
            rules = self.rules_map.get(name, {}); rop = rules.get("ReorderPoint", ""); soq = rules.get("StandardOrderQuantity", "")
            self.materials_table.setItem(r, 2, QTableWidgetItem(str(rop))); self.materials_table.setItem(r, 3, QTableWidgetItem(str(soq)))

    def clear_all_fields(self):
        for editor in [self.name_edit, self.web_edit, self.mail_edit, self.contact_edit, self.phone_edit, self.order_web_edit]: editor.clear()
        self.method_combo.setCurrentIndex(0); self.materials_table.setRowCount(0)
        self.current_selected_supplier_key = None; self.supplier_list_widget.clearSelection()

if __name__ == '__main__':
    app = QApplication(sys.argv); win = CentralHubGUI(); win.show(); sys.e
