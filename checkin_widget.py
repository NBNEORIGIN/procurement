import logging
import traceback
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                            QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
                            QAbstractItemView, QLabel, QComboBox, QLineEdit, QDateEdit) # Removed QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QDoubleValidator

from database import db
from order_processing import receive_order, process_order # Added imports

# Set up logger
logger = logging.getLogger('procurement.checkin')

class CheckInWidget(QWidget):
    """Widget for managing order check-ins and updating inventory."""
    
    # Signal emitted when check-ins are processed or orders processed
    data_changed = pyqtSignal() # Renamed for broader use
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_connections()
        self.load_pending_orders()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header with title and buttons
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Order Management & Receiving") # Updated title
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.refresh_btn = QPushButton("Refresh")
        # self.process_btn = QPushButton("Process Check-Ins") # Removed
        # self.process_btn.setEnabled(False) # Removed
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)
        # header_layout.addWidget(self.process_btn) # Removed
        
        # Table setup
        self.table = QTableWidget()
        self.table.setColumnCount(11) # Adjusted column count
        self.table.setHorizontalHeaderLabels([
            "Order ID", "Material", "Type", "Supplier", "Ordered Qty",
            "Is Processed?", "Total Received", "New Receipt Qty",
            "New Receipt Status", "Receipt Date", "Actions"
        ])
        
        # Configure table properties
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Keep as NoEditTriggers for main table
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection) # Changed from NoSelection
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True) # Or adjust last few columns
        self.table.verticalHeader().setVisible(False)
        
        # Set column widths (adjust as needed)
        self.table.setColumnWidth(0, 70)    # Order ID
        self.table.setColumnWidth(1, 150)   # Material
        self.table.setColumnWidth(2, 100)   # Type
        self.table.setColumnWidth(3, 120)   # Supplier
        self.table.setColumnWidth(4, 90)    # Ordered Qty
        self.table.setColumnWidth(5, 90)    # Is Processed?
        self.table.setColumnWidth(6, 100)   # Total Received
        self.table.setColumnWidth(7, 110)   # New Receipt Qty (LineEdit)
        self.table.setColumnWidth(8, 110)   # New Receipt Status (ComboBox)
        self.table.setColumnWidth(9, 100)   # Receipt Date (DateEdit)
        self.table.setColumnWidth(10, 150)  # Actions (Buttons)
        
        # Add widgets to layout
        layout.addLayout(header_layout)
        layout.addWidget(self.table)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: green;")
        layout.addWidget(self.status_label)
    
    def setup_connections(self):
        """Set up signal-slot connections."""
        self.refresh_btn.clicked.connect(self.load_pending_orders)
        # self.process_btn.clicked.connect(self.process_checkins) # Removed
    
    def load_pending_orders(self):
        """Load orders, their processing status, and received quantities."""
        try:
            self.table.setRowCount(0)
            conn = db.get_connection()
            cursor = conn.cursor()

            # Fetch orders with material details and total received quantity
            # o.id (0), m.name (1), m.type (2), m.supplier (3), o.order_qty (4),
            # o.is_processed (5), m.id (6) as material_id,
            # COALESCE(SUM(r.received_qty), 0) AS total_received (7)
            cursor.execute('''
                SELECT o.id, m.name, m.type, m.supplier, o.order_qty, o.is_processed,
                       m.id as material_id, COALESCE(SUM(r.received_qty), 0) AS total_received
                FROM orders o
                JOIN materials m ON o.material_id = m.id
                LEFT JOIN receipts r ON o.id = r.order_id
                GROUP BY o.id, m.name, m.type, m.supplier, o.order_qty, o.is_processed, m.id
                ORDER BY o.order_date DESC, o.id DESC
            ''')
            orders = cursor.fetchall()

            for row_idx, order_data in enumerate(orders):
                self.table.insertRow(row_idx)
                order_id = order_data[0]
                
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(order_id)))  # Order ID
                self.table.setItem(row_idx, 1, QTableWidgetItem(order_data[1]))  # Material Name
                self.table.setItem(row_idx, 2, QTableWidgetItem(order_data[2]))  # Material Type
                self.table.setItem(row_idx, 3, QTableWidgetItem(order_data[3] or ""))  # Supplier
                self.table.setItem(row_idx, 4, QTableWidgetItem(f"{order_data[4]:.2f}"))  # Ordered Qty
                
                is_processed_text = "Yes" if order_data[5] == 1 else "No"
                self.table.setItem(row_idx, 5, QTableWidgetItem(is_processed_text)) # Is Processed?
                
                total_received_qty = order_data[7]
                self.table.setItem(row_idx, 6, QTableWidgetItem(f"{total_received_qty:.2f}")) # Total Received

                # New Receipt Qty (Editable LineEdit)
                new_receipt_qty_edit = QLineEdit("0.00")
                new_receipt_qty_edit.setValidator(QDoubleValidator(0, 999999.99, 2, self))
                new_receipt_qty_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
                self.table.setCellWidget(row_idx, 7, new_receipt_qty_edit)

                # New Receipt Status (Editable ComboBox)
                receipt_status_combo = QComboBox()
                receipt_status_combo.addItems(["FULL", "PARTIAL", "WRONG"])
                self.table.setCellWidget(row_idx, 8, receipt_status_combo)
                
                # Receipt Date (Editable DateEdit)
                receipt_date_edit = QDateEdit(QDate.currentDate())
                receipt_date_edit.setCalendarPopup(True)
                receipt_date_edit.setDisplayFormat("yyyy-MM-dd")
                self.table.setCellWidget(row_idx, 9, receipt_date_edit)

                # Actions (Buttons)
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(5, 0, 5, 0) # Compact layout

                if order_data[5] == 0: # If not processed
                    process_button = QPushButton("Process")
                    process_button.setProperty("order_id", order_id)
                    process_button.clicked.connect(self.handle_process_order_button)
                    actions_layout.addWidget(process_button)
                
                add_receipt_button = QPushButton("Add Receipt")
                add_receipt_button.setProperty("order_id", order_id)
                add_receipt_button.setProperty("row", row_idx) # Pass current row for easy access
                add_receipt_button.clicked.connect(self.handle_add_receipt_button)
                actions_layout.addWidget(add_receipt_button)
                
                actions_layout.addStretch()
                self.table.setCellWidget(row_idx, 10, actions_widget)

            self.status_label.setText(f"Loaded {len(orders)} orders.")
        except Exception as e:
            logger.error(f"Failed to load orders: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load orders: {str(e)}")

    def handle_process_order_button(self):
        button = self.sender()
        if button:
            button.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.table.setEnabled(False)
        try:
            if not button: # Should not happen if called by button click
                logger.error("handle_process_order_button called without a sender.")
                return
            order_id = button.property("order_id")
            if order_id is None:
                logger.error("Process order button clicked, but no order_id property found.")
                return

            logger.info(f"Processing order ID: {order_id}")
            success = process_order(order_id)
            if success:
                QMessageBox.information(self, "Success", f"Order {order_id} marked as processed.")
                self.load_pending_orders() # Refresh table
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Failed", f"Failed to process order {order_id}. See logs for details.")
        finally:
            # Button might be gone if table reloaded. If so, it's fine.
            # The table itself being re-enabled is key.
            self.refresh_btn.setEnabled(True)
            self.table.setEnabled(True)
            # Re-enabling the specific button is tricky due to reload.
            # If button still exists and is the same instance, this would work:
            # if button and button.parent(): button.setEnabled(True)
            # However, load_pending_orders creates new button instances.

    def handle_add_receipt_button(self):
        button = self.sender()
        if button:
            button.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.table.setEnabled(False)
        
        try:
            if not button: # Should not happen
                logger.error("handle_add_receipt_button called without a sender.")
                return
                
            order_id = button.property("order_id")
            row = button.property("row")

            if order_id is None or row is None:
                logger.error("Add receipt button clicked, but order_id or row property missing.")
                return

            new_receipt_qty_widget = self.table.cellWidget(row, 7)
            receipt_status_widget = self.table.cellWidget(row, 8)

            if not new_receipt_qty_widget or not receipt_status_widget:
                QMessageBox.warning(self, "Error", "Could not find input widgets for receipt details.")
                return

            received_qty_str = new_receipt_qty_widget.text()
            received_qty = float(received_qty_str)
            status_value = receipt_status_widget.currentText()

            if received_qty <= 0 and status_value != "WRONG":
                QMessageBox.warning(self, "Invalid Quantity", "Received quantity must be greater than 0 for FULL or PARTIAL status.")
                return

            logger.info(f"Adding receipt for order ID: {order_id}, Row: {row}, Qty: {received_qty}, Status: {status_value}")
            
            success = receive_order(order_id, received_qty, status_value)
            
            if success:
                QMessageBox.information(self, "Success", f"Receipt added for order {order_id}.")
                self.load_pending_orders() # Refresh table
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Failed", f"Failed to add receipt for order {order_id}. See logs for details.")

        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Invalid quantity entered. Please enter a valid number.")
        except Exception as e:
            logger.error(f"Error in handle_add_receipt_button for order {order_id}, row {row}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
        finally:
            self.refresh_btn.setEnabled(True)
            self.table.setEnabled(True)
            # Specific button re-enabling is complex due to table reload creating new button instances.
            # if button and button.parent(): button.setEnabled(True)
