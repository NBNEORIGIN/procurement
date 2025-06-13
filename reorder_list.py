from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                            QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
                            QAbstractItemView, QLabel, QComboBox, QCheckBox, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QColor, QDoubleValidator

from database import db
from order_processing import create_order
import logging

logger = logging.getLogger('procurement.reorder_list')

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
            "", "ID", "Type", "Name", "Current Stock", "Min Stock",
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
                SELECT id, type, name, current_stock, min_stock, reorder_point, supplier
                FROM materials
                WHERE current_stock <= reorder_point
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
                
                # Current Stock (highlight if below reorder_point)
                # material[3] is current_stock, material[5] is reorder_point
                current_stock_item = QTableWidgetItem(f"{material[3]:.2f}")
                if material[3] <= material[5]: # current_stock <= reorder_point (though query already filters, this is for visual cue)
                    current_stock_item.setForeground(QColor('red'))
                self.table.setItem(row, 4, current_stock_item)
                
                # Min Stock
                self.table.setItem(row, 5, QTableWidgetItem(f"{material[4]:.2f}")) # material[4] is min_stock
                
                # Reorder Point
                self.table.setItem(row, 6, QTableWidgetItem(f"{material[5]:.2f}")) # material[5] is reorder_point
                
                # Supplier
                self.table.setItem(row, 7, QTableWidgetItem(material[6] or "")) # material[6] is supplier
                
                # Order Qty (editable)
                # Default to reorder_point - current_stock
                order_qty = max(material[5] - material[3], 0)
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
        """Create purchase orders for selected items using order_processing module."""
        self.create_order_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        try:
            # Get selected items
            order_items = []
            selected_rows_count = 0
            for row in range(self.table.rowCount()):
                checkbox_widget = self.table.cellWidget(row, 0)
                if not checkbox_widget:
                    continue
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_rows_count +=1
                    material_id_item = self.table.item(row, 1)
                    order_qty_widget = self.table.cellWidget(row, 8)
                    
                    if material_id_item and order_qty_widget:
                        try:
                            material_id = int(material_id_item.text())
                            quantity = float(order_qty_widget.text() or "0")
                            if quantity > 0:
                                order_items.append({'material_id': material_id, 'quantity': quantity, 'row': row})
                            else:
                                logger.warning(f"Skipping row {row} for order creation: quantity is zero or invalid.")
                        except ValueError:
                            logger.error(f"Invalid data in row {row} for order creation.", exc_info=True)
                            continue
                    else:
                        logger.warning(f"Missing material_id_item or order_qty_widget in row {row}")


            if not order_items:
                QMessageBox.warning(self, "No Valid Items", "No valid items selected or quantities specified for ordering.")
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
                successful_orders = 0
                failed_orders = 0
                
                for item_data in order_items:
                    material_id = item_data['material_id']
                    quantity = item_data['quantity']
                    row = item_data['row']

                    new_order_id = create_order(material_id, quantity)
                    if new_order_id:
                        logger.info(f"Successfully created order for material ID {material_id}, quantity {quantity}. New Order ID: {new_order_id}")
                        successful_orders += 1
                    else:
                        logger.error(f"Failed to create order for material ID {material_id}, quantity {quantity}. See previous logs for details.")
                        failed_orders += 1
                        # Optionally, provide visual feedback on the row that failed
                        order_qty_widget = self.table.cellWidget(row, 8)
                        if order_qty_widget:
                            order_qty_widget.setStyleSheet("background-color: #ffdddd;")


                summary_message = f"Successfully created {successful_orders} order(s)."
                if failed_orders > 0:
                    summary_message += f"\nFailed to create {failed_orders} order(s)."
                
                QMessageBox.information(self, "Order Creation Summary", summary_message)
                self.status_label.setText(summary_message)

                if successful_orders > 0:
                    self.orders_created.emit()
                    self.load_reorder_items() # Refresh the list
            else:
                logger.info("User cancelled order creation.")
                self.status_label.setText("Order creation cancelled by user.")

        except Exception as e:
            logger.error(f"An unexpected error occurred in create_orders: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to create orders: {str(e)}")
        finally:
            self.update_order_button_state() # Re-evaluates create_order_btn state
            self.refresh_btn.setEnabled(True)
