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
        self.setGeometry(100, 100, 700, 500) # x, y, width, height

        self.suppliers_data = self.load_suppliers()
        self.current_selected_supplier_key = None

        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left panel: Supplier list
        left_panel_layout = QVBoxLayout()
        left_panel_layout.addWidget(QLabel("Suppliers:"))
        self.supplier_list_widget = QListWidget()
        self.supplier_list_widget.itemClicked.connect(self.on_supplier_selected)
        left_panel_layout.addWidget(self.supplier_list_widget)
        
        main_layout.addLayout(left_panel_layout, 1) # Proportion 1

        # Right panel: Details and controls
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

        self.details_form_layout.addRow("Supplier Name:", self.supplier_name_edit)
        self.details_form_layout.addRow("Website (Info):", self.website_edit)
        self.details_form_layout.addRow("Email:", self.email_edit)
        self.details_form_layout.addRow("Contact Person:", self.contact_person_edit)
        self.details_form_layout.addRow("Phone:", self.phone_edit)
        self.details_form_layout.addRow("Order Method:", self.order_method_combo)
        self.details_form_layout.addRow("Supplier Website (Ordering):", self.supplier_website_edit)
        
        right_panel_layout.addLayout(self.details_form_layout)

        # Buttons
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

        main_layout.addLayout(right_panel_layout, 2) # Proportion 2

        self.populate_supplier_list()
        self.clear_detail_fields()

    def load_suppliers(self):
        try:
            with open(SUPPLIERS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            QMessageBox.information(self, "Info", f"{SUPPLIERS_FILE} not found. A new one will be created on save.")
            return {}
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Error", f"Error decoding {SUPPLIERS_FILE}. Check its format.")
            return {}

    def save_suppliers_to_file(self):
        try:
            with open(SUPPLIERS_FILE, 'w') as f:
                json.dump(self.suppliers_data, f, indent=4)
            QMessageBox.information(self, "Success", "Supplier data saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save supplier data: {e}")

    def populate_supplier_list(self):
        self.supplier_list_widget.clear()
        if self.suppliers_data:
            for supplier_name in sorted(self.suppliers_data.keys()):
                self.supplier_list_widget.addItem(supplier_name)

    def on_supplier_selected(self, item):
        self.current_selected_supplier_key = item.text()
        supplier_details = self.suppliers_data.get(self.current_selected_supplier_key, {})
        
        self.supplier_name_edit.setText(self.current_selected_supplier_key)
        self.website_edit.setText(supplier_details.get("website", ""))
        self.email_edit.setText(supplier_details.get("email", ""))
        self.contact_person_edit.setText(supplier_details.get("contact_person", ""))
        self.phone_edit.setText(supplier_details.get("phone", ""))
        
        order_method = supplier_details.get("order_method", "")
        if order_method in [self.order_method_combo.itemText(i) for i in range(self.order_method_combo.count())]:
            self.order_method_combo.setCurrentText(order_method)
        else:
            self.order_method_combo.setCurrentIndex(0)

        self.supplier_website_edit.setText(supplier_details.get("supplier_website", ""))
        self.supplier_name_edit.setReadOnly(True)

    def clear_detail_fields(self, new_supplier_mode=False):
        if new_supplier_mode:
            self.supplier_name_edit.setReadOnly(False)
            self.supplier_name_edit.setPlaceholderText("Enter New Supplier Name")
        else:
            self.supplier_name_edit.setReadOnly(True)
            self.supplier_name_edit.setPlaceholderText("")

        self.supplier_name_edit.clear()
        self.website_edit.clear()
        self.email_edit.clear()
        self.contact_person_edit.clear()
        self.phone_edit.clear()
        self.order_method_combo.setCurrentIndex(0)
        self.supplier_website_edit.clear()
        self.current_selected_supplier_key = None
        self.supplier_list_widget.clearSelection()

    def add_new_supplier(self):
        self.clear_detail_fields(new_supplier_mode=True)
        self.supplier_name_edit.setFocus()
        QMessageBox.information(self, "Add Supplier", "Enter details for the new supplier and click 'Save Changes'. Name must be unique.")

    def save_supplier_changes(self):
        supplier_key_to_save = self.supplier_name_edit.text().strip()
        if not supplier_key_to_save:
            QMessageBox.warning(self, "Input Error", "Supplier Name cannot be empty.")
            return

        is_editing_existing = self.supplier_name_edit.isReadOnly() and self.current_selected_supplier_key
        
        if is_editing_existing:
            supplier_key_to_save = self.current_selected_supplier_key # Use the original key
        elif supplier_key_to_save in self.suppliers_data and (not self.current_selected_supplier_key or supplier_key_to_save != self.current_selected_supplier_key) :
             QMessageBox.warning(self, "Input Error", f"Supplier name '{supplier_key_to_save}' already exists.")
             return

        current_details = self.suppliers_data.get(supplier_key_to_save, {})
        current_details["website"] = self.website_edit.text().strip()
        current_details["email"] = self.email_edit.text().strip()
        current_details["contact_person"] = self.contact_person_edit.text().strip()
        current_details["phone"] = self.phone_edit.text().strip()
        current_details["order_method"] = self.order_method_combo.currentText()
        current_details["supplier_website"] = self.supplier_website_edit.text().strip()
        if not current_details["order_method"]: current_details["order_method"] = ""

        self.suppliers_data[supplier_key_to_save] = current_details
        self.save_suppliers_to_file()
        self.populate_supplier_list()

        items = self.supplier_list_widget.findItems(supplier_key_to_save, Qt.MatchFlag.MatchExactly)
        if items:
            self.supplier_list_widget.setCurrentItem(items[0])
            self.on_supplier_selected(items[0])
        self.supplier_name_edit.setReadOnly(True)

    def delete_supplier(self):
        if not self.current_selected_supplier_key:
            QMessageBox.warning(self, "Selection Error", "Please select a supplier to delete.")
            return
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete '{self.current_selected_supplier_key}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.current_selected_supplier_key in self.suppliers_data:
                del self.suppliers_data[self.current_selected_supplier_key]
                self.save_suppliers_to_file()
                self.populate_supplier_list()
                self.clear_detail_fields()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = SupplierManagerGUI()
    main_window.show()
    sys.exit(app.exec())
