from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                            QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
                            QAbstractItemView, QLineEdit, QLabel, QComboBox, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QAction, QIcon

from database import db

class MaterialsListWidget(QWidget):
    """Widget to display and manage a list of materials."""
    
    # Signal emitted when a material is selected for editing
    edit_requested = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_connections()
        self.load_materials()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Search and filter bar
        search_layout = QHBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search materials...")
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Types", "all")
        
        refresh_btn = QPushButton("Refresh")
        
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(QLabel("Filter by Type:"))
        search_layout.addWidget(self.filter_combo)
        search_layout.addWidget(refresh_btn)
        search_layout.addStretch()
        
        # Table setup
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Type", "Name", "Unit", "Current Stock", "Min Stock",
            "Supplier", "Order URL", "Actions"
        ])
        
        # Configure table properties
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        
        # Add widgets to layout
        layout.addLayout(search_layout)
        layout.addWidget(self.table)
        
        # Set size policy
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), 
                          QSizePolicy.Policy.Expanding)
    
    def setup_connections(self):
        """Set up signal-slot connections."""
        self.search_edit.textChanged.connect(self.filter_materials)
        self.filter_combo.currentTextChanged.connect(self.filter_materials)
    
    def load_materials(self):
        """Load materials from the database and populate the table."""
        try:
            # Clear existing data
            self.table.setRowCount(0)
            
            # Get materials from database
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials ORDER BY type, name")
            materials = cursor.fetchall()
            
            # Update type filter
            self.update_type_filter(materials)
            
            # Populate table
            for row, material in enumerate(materials):
                self.table.insertRow(row)
                
                # Add data to columns
                # Indices based on SELECT * and new table structure:
                # id:0, type:1, name:2, unit:3, current_stock:4, min_stock:5,
                # reorder_point:6, order_method:7, supplier:8, order_url:9,
                # contact:10, notes:11, created_at:12, updated_at:13
                self.table.setItem(row, 0, QTableWidgetItem(str(material[0])))  # ID
                self.table.setItem(row, 1, QTableWidgetItem(material[1]))  # Type
                self.table.setItem(row, 2, QTableWidgetItem(material[2]))  # Name
                self.table.setItem(row, 3, QTableWidgetItem(material[3]))  # Unit
                self.table.setItem(row, 4, QTableWidgetItem(str(material[4])))  # Current Stock
                self.table.setItem(row, 5, QTableWidgetItem(str(material[5])))  # Min Stock
                self.table.setItem(row, 6, QTableWidgetItem(material[8] or ""))  # Supplier
                self.table.setItem(row, 7, QTableWidgetItem(material[9] or ""))  # Order URL
                
                # Add action buttons
                btn_layout = QHBoxLayout()
                btn_widget = QWidget()
                
                edit_btn = QPushButton("Edit")
                edit_btn.setProperty('material_id', material[0])
                edit_btn.clicked.connect(self.on_edit_clicked)
                
                delete_btn = QPushButton("Delete")
                delete_btn.setProperty('material_id', material[0])
                delete_btn.clicked.connect(self.on_delete_clicked)
                
                btn_layout.addWidget(edit_btn)
                btn_layout.addWidget(delete_btn)
                btn_layout.setContentsMargins(5, 1, 5, 1)
                
                btn_widget.setLayout(btn_layout)
                self.table.setCellWidget(row, 8, btn_widget) # Actions button in column 8
            
            # Resize columns to contents
            self.table.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load materials: {str(e)}")
    
    def update_type_filter(self, materials):
        """Update the type filter dropdown with unique material types."""
        current_filter = self.filter_combo.currentText()
        self.filter_combo.clear()
        self.filter_combo.addItem("All Types", "all")
        
        # Get unique types
        types = sorted(list(set(m[1] for m in materials)))
        for type_name in types:
            if type_name:  # Skip empty types
                self.filter_combo.addItem(type_name, type_name)
        
        # Restore previous selection if it still exists
        index = self.filter_combo.findText(current_filter)
        if index >= 0:
            self.filter_combo.setCurrentIndex(index)
    
    def filter_materials(self):
        """Filter materials based on search text and type filter."""
        search_text = self.search_edit.text().lower()
        filter_type = self.filter_combo.currentData()
        
        for row in range(self.table.rowCount()):
            should_show = True
            
            # Apply type filter
            if filter_type != "all":
                type_item = self.table.item(row, 1)  # Type column
                if type_item and type_item.text() != filter_type:
                    should_show = False
            
            # Apply search filter
            if should_show and search_text:
                row_matches = False
                for col in range(self.table.columnCount() - 1):  # Skip actions column
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        row_matches = True
                        break
                should_show = row_matches
            
            # Show/hide row
            self.table.setRowHidden(row, not should_show)
    
    def on_edit_clicked(self):
        """Handle edit button click."""
        button = self.sender()
        material_id = button.property('material_id')
        self.edit_material(material_id)
    
    def on_delete_clicked(self):
        """Handle delete button click."""
        button = self.sender()
        material_id = button.property('material_id')
        
        reply = QMessageBox.question(
            self, 'Delete Material',
            'Are you sure you want to delete this material?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_material(material_id)
    
    def edit_material(self, material_id):
        """Emit signal to edit the selected material."""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
            material = cursor.fetchone()
            
            if material:
                # Indices based on SELECT * and new table structure:
                # id:0, type:1, name:2, unit:3, current_stock:4, min_stock:5,
                # reorder_point:6, order_method:7, supplier:8, order_url:9,
                # contact:10, notes:11, created_at:12, updated_at:13
                material_dict = {
                    'id': material[0],
                    'type': material[1],
                    'name': material[2],
                    'unit': material[3],
                    'current_stock': material[4],
                    'min_stock': material[5],
                    'reorder_point': material[6],
                    'order_method': material[7],
                    'supplier': material[8],
                    'order_url': material[9],
                    'contact': material[10],
                    'notes': material[11]
                }
                self.edit_requested.emit(material_dict)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit material: {str(e)}")
    
    def delete_material(self, material_id):
        """Delete the selected material from the database."""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Check for dependent records
            cursor.execute("SELECT COUNT(*) FROM orders WHERE material_id = ?", (material_id,))
            if cursor.fetchone()[0] > 0:
                QMessageBox.warning(
                    self,
                    "Cannot Delete",
                    "This material has associated orders and cannot be deleted."
                )
                return
            
            # Delete the material
            cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            conn.commit()
            
            # Reload materials
            self.load_materials()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete material: {str(e)}")
