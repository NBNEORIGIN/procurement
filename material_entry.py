from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                            QLineEdit, QComboBox, QPushButton, QMessageBox,
                            QLabel, QScrollArea, QDoubleSpinBox, QSizePolicy)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices
from database import db

class ClickableLabel(QLabel):
    """A clickable label that opens a URL when clicked."""
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.setOpenExternalLinks(True)
        self.setStyleSheet("color: blue; text-decoration: underline;")

class MaterialEntryWidget(QWidget):
    """Widget for adding and editing materials."""
    
    # Signal emitted when a material is saved
    material_saved = pyqtSignal()
    
    def __init__(self, material_data=None):
        """Initialize the widget.
        
        Args:
            material_data (dict, optional): Material data for editing. If None, create new material.
        """
        super().__init__()
        self.material_id = material_data.get('id') if material_data else None
        self.setup_ui()
        self.setup_connections()
        
        # If editing, populate the form
        if material_data:
            self.populate_form(material_data)
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)
        
        # Form fields
        self.type_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["kg", "g", "L", "mL", "pcs", "m", "cm", "mm"])
        
        self.current_stock_spinbox = QDoubleSpinBox()
        self.current_stock_spinbox.setRange(0, 999999.99)
        self.current_stock_spinbox.setDecimals(2)
        
        self.min_stock_spinbox = QDoubleSpinBox()
        self.min_stock_spinbox.setRange(0, 999999.99)
        self.min_stock_spinbox.setDecimals(2)
        
        self.reorder_point = QDoubleSpinBox()
        self.reorder_point.setRange(0, 999999.99)
        self.reorder_point.setDecimals(2)
        
        self.order_method = QComboBox()
        self.order_method.addItems(["Email", "Phone", "Online", "In-Person"])
        
        self.supplier_edit = QLineEdit()
        self.order_url_edit = QLineEdit()
        self.contact_edit = QLineEdit()
        self.notes_edit = QLineEdit()
        
        # Add fields to form
        form_layout.addRow("Type*:", self.type_edit)
        form_layout.addRow("Name*:", self.name_edit)
        form_layout.addRow("Unit*:", self.unit_combo)
        form_layout.addRow("Current Stock:", self.current_stock_spinbox)
        form_layout.addRow("Min Stock:", self.min_stock_spinbox)
        form_layout.addRow("Reorder Point:", self.reorder_point)
        form_layout.addRow("Order Method:", self.order_method)
        form_layout.addRow("Supplier:", self.supplier_edit)
        form_layout.addRow("Order URL:", self.order_url_edit)
        form_layout.addRow("Contact:", self.contact_edit)
        form_layout.addRow("Notes:", self.notes_edit)
        
        # Set up scroll area
        scroll.setWidget(scroll_content)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Material")
        self.clear_btn = QPushButton("Clear Form")
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.clear_btn)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: green;")
        
        # Add widgets to main layout
        layout.addWidget(scroll)
        layout.addLayout(button_layout)
        layout.addWidget(self.status_label)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    def setup_connections(self):
        """Set up signal-slot connections."""
        self.save_btn.clicked.connect(self.save_material)
        self.clear_btn.clicked.connect(self.clear_form)
    
    def validate_form(self):
        """Validate the form inputs."""
        errors = []
        
        if not self.type_edit.text().strip():
            errors.append("Type is required.")
        if not self.name_edit.text().strip():
            errors.append("Name is required.")
        if not self.unit_combo.currentText():
            errors.append("Unit is required.")
            
        # Validate numeric fields
        try:
            float(self.current_stock_spinbox.value())
            float(self.min_stock_spinbox.value())
            float(self.reorder_point.value())
        except ValueError:
            errors.append("Quantity fields must be valid numbers.")
            
        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return False
            
        return True
    
    def save_material(self):
        """Save the material to the database."""
        if not self.validate_form():
            return
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            material_data = (
                self.type_edit.text().strip(),
                self.name_edit.text().strip(),
                self.unit_combo.currentText(),
                self.current_stock_spinbox.value(),
                self.min_stock_spinbox.value(),
                self.reorder_point.value(),
                self.order_method.currentText(),
                self.supplier_edit.text().strip(),
                self.order_url_edit.text().strip(),
                self.contact_edit.text().strip(),
                self.notes_edit.text().strip()
            )
            
            if self.material_id:
                # Update existing material
                cursor.execute('''
                    UPDATE materials SET
                        type = ?, name = ?, unit = ?, current_stock = ?,
                        min_stock = ?, reorder_point = ?, order_method = ?,
                        supplier = ?, order_url = ?, contact = ?, notes = ?
                    WHERE id = ?
                ''', material_data + (self.material_id,))
                action = "updated"
            else:
                # Insert new material
                cursor.execute('''
                    INSERT INTO materials (
                        type, name, unit, current_stock, min_stock, reorder_point,
                        order_method, supplier, order_url, contact, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', material_data)
                action = "saved"
            
            conn.commit()
            self.status_label.setText(f"Material {action} successfully!")
            
            # Emit signal to notify parent
            self.material_saved.emit()
            
            # If this was a new material, clear the form for the next entry
            if not self.material_id:
                self.clear_form()
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save material: {str(e)}")
    def clear_form(self):
        """Clear all form fields and reset to add mode."""
        self.material_id = None
        self.type_edit.clear()
        self.name_edit.clear()
        self.unit_combo.setCurrentIndex(0)
        self.current_stock_spinbox.setValue(0.0)
        self.min_stock_spinbox.setValue(0.0)
        self.reorder_point.setValue(0.0)
        self.order_method.setCurrentIndex(0)
        self.supplier_edit.clear()
        self.order_url_edit.clear()
        self.contact_edit.clear()
        self.notes_edit.clear()
        self.status_label.clear()
        
    def populate_form(self, material_data):
        """Populate the form with material data for editing.
        
        Args:
            material_data (dict): Dictionary containing material data
        """
        self.material_id = material_data.get('id')
        self.type_edit.setText(material_data.get('type', ''))
        self.name_edit.setText(material_data.get('name', ''))
        
        # Set unit
        unit_index = self.unit_combo.findText(material_data.get('unit', ''))
        if unit_index >= 0:
            self.unit_combo.setCurrentIndex(unit_index)
            
        # Set numeric fields
        self.current_stock_spinbox.setValue(float(material_data.get('current_stock', 0)))
        self.min_stock_spinbox.setValue(float(material_data.get('min_stock', 0)))
        self.reorder_point.setValue(float(material_data.get('reorder_point', 0)))
        
        # Set order method
        method_index = self.order_method.findText(material_data.get('order_method', ''))
        if method_index >= 0:
            self.order_method.setCurrentIndex(method_index)
            
        # Set remaining fields
        self.supplier_edit.setText(material_data.get('supplier', ''))
        self.order_url_edit.setText(material_data.get('order_url', ''))
        self.contact_edit.setText(material_data.get('contact', ''))
        self.notes_edit.setText(material_data.get('notes', ''))
