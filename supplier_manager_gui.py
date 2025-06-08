import sys
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLineEdit, QPushButton, QLabel, QFormLayout,
    QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt

SUPPLIERS_FILE = "suppliers.json"

class SupplierManagerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Supplier Manager")
        self.setGeometry(100, 100, 750, 550)

        self.suppliers_data = self.load_suppliers()
        self.current_selected_supplier_key = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        left_panel_layout = QVBoxLayout()
        left_panel_layout.addWidget(QLabel("Suppliers:"))
        self.supplier_list_widget = QListWidget()
        self.supplier_list_widget.itemClicked.connect(self.on_supplier_selected)
        left_panel_layout.addWidget(self.supplier_list_widget)
        main_layout.addLayout(left_panel_layout, 1)

        right_panel_layout = QVBoxLayout()
        self.details_form_layout = QFormLayout()

        self.supplier_name_edit = QLineEdit()
        self.supplier_name_edit.setReadOnly(True)
        self.website_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.contact_person_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.order_method_combo = QComboBox()
        self.order_method_combo.addItems(["", "email", "online", "phone", "other"])
        self.supplier_website_edit = QLineEdit()
        self.materials_supplied_edit = QLineEdit() # NEW
        self.materials_supplied_edit.setPlaceholderText("Comma-separated list of materials")

        self.details_form_layout.addRow("Supplier Name:", self.supplier_name_edit)
        self.details_form_layout.addRow("Website (Info):", self.website_edit)
        self.details_form_layout.addRow("Email:", self.email_edit)
        self.details_form_layout.addRow("Contact Person:", self.contact_person_edit)
        self.details_form_layout.addRow("Phone:", self.phone_edit)
        self.details_form_layout.addRow("Order Method:", self.order_method_combo)
        self.details_form_layout.addRow("Supplier Website (Ordering):", self.supplier_website_edit)
        self.details_form_layout.addRow("Materials Supplied:", self.materials_supplied_edit) # NEW
        
        right_panel_layout.addLayout(self.details_form_layout)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add New Supplier")
        self.add_button.clicked.connect(self.add_new_supplier)
        self.save_button = QPushButton("Save Changes")
        self.save_button.clicked.connect(self.save_supplier_changes)
        self.delete_button = QPushButton("Delete Supplier")
        self.delete_button.clicked.connect(self.delete_supplier)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.delete_button)
        right_panel_layout.addLayout(button_layout)
        main_layout.addLayout(right_panel_layout, 2)

        self.populate_supplier_list()
        self.clear_detail_fields()

    def load_suppliers(self):
        try:
            with open(SUPPLIERS_FILE, 'r') as f: return json.load(f)
        except FileNotFoundError: return {}
        except json.JSONDecodeError: return {}

    def save_suppliers_to_file(self):
        try:
            with open(SUPPLIERS_FILE, 'w') as f: json.dump(self.suppliers_data, f, indent=4)
            QMessageBox.information(self, "Success", "Supplier data saved.")
        except Exception as e: QMessageBox.critical(self, "Error", f"Could not save: {e}")

    def populate_supplier_list(self):
        self.supplier_list_widget.clear()
        if self.suppliers_data:
            for name in sorted(self.suppliers_data.keys()): self.supplier_list_widget.addItem(name)

    def on_supplier_selected(self, item):
        self.current_selected_supplier_key = item.text()
        details = self.suppliers_data.get(self.current_selected_supplier_key, {})
        self.supplier_name_edit.setText(self.current_selected_supplier_key)
        self.website_edit.setText(details.get("website", ""))
        self.email_edit.setText(details.get("email", ""))
        self.contact_person_edit.setText(details.get("contact_person", ""))
        self.phone_edit.setText(details.get("phone", ""))
        om = details.get("order_method", "")
        self.order_method_combo.setCurrentText(om) if om in [self.order_method_combo.itemText(i) for i in range(self.order_method_combo.count())] else self.order_method_combo.setCurrentIndex(0)
        self.supplier_website_edit.setText(details.get("supplier_website", ""))
        materials = details.get("materials_supplied", []) # NEW
        self.materials_supplied_edit.setText(", ".join(materials)) # NEW
        self.supplier_name_edit.setReadOnly(True)

    def clear_detail_fields(self, new_mode=False):
        self.supplier_name_edit.setReadOnly(not new_mode)
        self.supplier_name_edit.setPlaceholderText("Enter New Supplier Name" if new_mode else "")
        for editor in [self.supplier_name_edit, self.website_edit, self.email_edit, 
                       self.contact_person_edit, self.phone_edit, 
                       self.supplier_website_edit, self.materials_supplied_edit]: # NEWLY ADDED
            editor.clear()
        self.order_method_combo.setCurrentIndex(0)
        self.current_selected_supplier_key = None
        self.supplier_list_widget.clearSelection()

    def add_new_supplier(self):
        self.clear_detail_fields(new_mode=True)
        self.supplier_name_edit.setFocus()

    def save_supplier_changes(self):
        key = self.supplier_name_edit.text().strip()
        if not key: QMessageBox.warning(self, "Input Error", "Supplier Name empty."); return
        
        editing_existing = self.supplier_name_edit.isReadOnly() and self.current_selected_supplier_key
        if editing_existing: key = self.current_selected_supplier_key
        elif key in self.suppliers_data and (not self.current_selected_supplier_key or key != self.current_selected_supplier_key):
             QMessageBox.warning(self, "Input Error", f"Supplier '{key}' already exists."); return

        details = self.suppliers_data.get(key, {})
        details["website"] = self.website_edit.text().strip()
        details["email"] = self.email_edit.text().strip()
        details["contact_person"] = self.contact_person_edit.text().strip()
        details["phone"] = self.phone_edit.text().strip()
        details["order_method"] = self.order_method_combo.currentText() or ""
        details["supplier_website"] = self.supplier_website_edit.text().strip()
        
        materials_text = self.materials_supplied_edit.text().strip() # NEW
        details["materials_supplied"] = [m.strip() for m in materials_text.split(',') if m.strip()] if materials_text else [] #NEW

        self.suppliers_data[key] = details
        self.save_suppliers_to_file()
        self.populate_supplier_list()
        
        items = self.supplier_list_widget.findItems(key, Qt.MatchFlag.MatchExactly)
        if items: self.supplier_list_widget.setCurrentItem(items[0]); self.on_supplier_selected(items[0])
        self.supplier_name_edit.setReadOnly(True)

    def delete_supplier(self):
        if not self.current_selected_supplier_key: return
        if QMessageBox.question(self, "Confirm", f"Delete '{self.current_selected_supplier_key}'?", 
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self.current_selected_supplier_key in self.suppliers_data:
                del self.suppliers_data[self.current_selected_supplier_key]
                self.save_suppliers_to_file(); self.populate_supplier_list(); self.clear_detail_fields()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = SupplierManagerGUI(); win.show()
    sys.exit(app.exec())
