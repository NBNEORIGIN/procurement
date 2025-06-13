from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                            QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
                            QAbstractItemView, QLabel, QComboBox, QCheckBox, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QColor, QDoubleValidator

from database import db

class ReorderListWidget(QWidget):
    """Widget for managing materials that need to be reordered."""
    
    # Signal emitted when orders are created
    orders_created = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_connections()
        self.load_reorder_items()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header with title and buttons
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Items Below Reorder Point")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.refresh_btn = QPushButton("Refresh")
        self.create_order_btn = QPushButton("Create Orders")
        self.create_order_btn.setEnabled(False)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(self.create_order_btn)
        
        # Table setup
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "", "ID", "Type", "Name", "Current Qty", "Min Qty", 
            "Reorder Point", "Supplier", "Order Qty"
        ])
        
        # Configure table properties
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        
        # Set column widths
        self.table.setColumnWidth(0, 30)  # Checkbox
        self.table.setColumnWidth(1, 50)   # ID
        self.table.setColumnWidth(2, 100)  # Type
        self.table.setColumnWidth(3, 200)  # Name
        self.table.setColumnWidth(4, 80)   # Current Qty
        self.table.setColumnWidth(5, 80)   # Min Qty
        self.table.setColumnWidth(6, 100)  # Reorder Point
        self.table.setColumnWidth(7, 150)  # Supplier
        
        # Add widgets to layout
        layout.addLayout(header_layout)
        layout.addWidget(self.table)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: green;")
        layout.addWidget(self.status_label)
    
    def setup_connections(self):
        """Set up signal-slot connections."""
        self.refresh_btn.clicked.connect(self.load_reorder_items)
        self.create_order_btn.clicked.connect(self.create_orders)
    
    def load_reorder_items(self):
        """Load materials that are below their reorder point."""
        try:
            # Clear existing data
            self.table.setRowCount(0)
            
            # Get materials below reorder point
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, type, name, current_qty, min_qty, reorder_point, supplier
                FROM materials
                WHERE current_qty <= reorder_point
                ORDER BY type, name
            ''')
            
            materials = cursor.fetchall()
            
            # Populate table
            for row, material in enumerate(materials):
                self.table.insertRow(row)
                
                # Add checkbox
                checkbox = QCheckBox()
                checkbox.stateChanged.connect(self.update_order_button_state)
                
                cell_widget = QWidget()
                layout = QHBoxLayout(cell_widget)
                layout.addWidget(checkbox)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                cell_widget.setLayout(layout)
                
                self.table.setCellWidget(row, 0, cell_widget)
                
                # Add data to columns
                self.table.setItem(row, 1, QTableWidgetItem(str(material[0])))  # ID
                self.table.setItem(row, 2, QTableWidgetItem(material[1]))  # Type
                self.table.setItem(row, 3, QTableWidgetItem(material[2]))  # Name
                
                # Current Qty (highlight if below min)
                current_qty_item = QTableWidgetItem(f"{material[3]:.2f}")
                if material[3] < material[5]:  # current_qty < reorder_point
                    current_qty_item.setForeground(QColor('red'))
                self.table.setItem(row, 4, current_qty_item)
                
                # Min Qty
                self.table.setItem(row, 5, QTableWidgetItem(f"{material[4]:.2f}"))
                
                # Reorder Point
                self.table.setItem(row, 6, QTableWidgetItem(f"{material[5]:.2f}"))
                
                # Supplier
                self.table.setItem(row, 7, QTableWidgetItem(material[6] or ""))
                
                # Order Qty (editable)
                order_qty = max(material[5] - material[3], 0)  # Default to reorder_point - current_qty
                order_qty_item = QLineEdit(f"{order_qty:.2f}")
                order_qty_item.setValidator(QDoubleValidator(0, 999999, 2, self))
                order_qty_item.setAlignment(Qt.AlignmentFlag.AlignRight)
                order_qty_item.textChanged.connect(self.validate_order_quantities)
                self.table.setCellWidget(row, 8, order_qty_item)
            
            # Update status
            self.status_label.setText(f"Found {len(materials)} items below reorder point.")
            
            # Update order button state
            self.update_order_button_state()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load reorder items: {str(e)}")
    
    def update_order_button_state(self):
        """Enable/disable the Create Orders button based on selection."""
        has_selection = False
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                has_selection = True
                break
        
        self.create_order_btn.setEnabled(has_selection)
    
    def validate_order_quantities(self):
        """Validate order quantities and update UI accordingly."""
        for row in range(self.table.rowCount()):
            order_qty_edit = self.table.cellWidget(row, 8)
            if order_qty_edit:
                try:
                    qty = float(order_qty_edit.text() or "0")
                    if qty <= 0:
                        order_qty_edit.setStyleSheet("background-color: #ffdddd;")
                    else:
                        order_qty_edit.setStyleSheet("")
                except ValueError:
                    order_qty_edit.setStyleSheet("background-color: #ffdddd;")
    
    def create_orders(self):
        """Create purchase orders for selected items."""
        try:
            # Get current date
            order_date = QDate.currentDate().toString("yyyy-MM-dd")
            
            # Get selected items
            order_items = []
            for row in range(self.table.rowCount()):
                checkbox = self.table.cellWidget(row, 0).findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    material_id = int(self.table.item(row, 1).text())
                    order_qty_edit = self.table.cellWidget(row, 8)
                    
                    try:
                        quantity = float(order_qty_edit.text() or "0")
                        if quantity > 0:
                            order_items.append((material_id, quantity))
                    except ValueError:
                        continue
            
            if not order_items:
                QMessageBox.warning(self, "No Valid Items", "No valid items selected for ordering.")
                return
            
            # Confirm before creating orders
            reply = QMessageBox.question(
                self,
                "Confirm Orders",
                f"Create orders for {len(order_items)} item(s)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                conn = db.get_connection()
                cursor = conn.cursor()
                
                for material_id, quantity in order_items:
                    cursor.execute('''
                        INSERT INTO orders (material_id, quantity_ordered, status, order_date)
                        VALUES (?, ?, 'Pending', ?)
                    ''', (material_id, quantity, order_date))
                
                conn.commit()
                
                # Update status and refresh
                self.status_label.setText(f"Created {len(order_items)} order(s) successfully.")
                self.orders_created.emit()
                
                # Refresh the list
                self.load_reorder_items()
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Orders Created",
                    f"Successfully created {len(order_items)} order(s).",
                    QMessageBox.StandardButton.Ok
                )
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create orders: {str(e)}")
