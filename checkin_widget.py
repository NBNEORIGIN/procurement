import logging
import traceback
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                            QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
                            QAbstractItemView, QLabel, QComboBox, QLineEdit, QDateEdit) # Removed QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QDoubleValidator

from database import db
from order_processing import receive_order, process_order
from analytics_functions import ( # Added imports for analytics
    calculate_average_lead_time_per_material,
    calculate_average_order_quantity_per_material,
    count_recent_orders_per_material
)

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
        self.refresh_all_views() # Changed from load_pending_orders to load both
    
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

        # History Table
        history_title_label = QLabel("Order History")
        history_title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(history_title_label)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Order ID", "Material Name", "Order Date", "Ordered Qty",
            "Processed?", "Total Received", "Overall Status"
        ])
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.history_table.horizontalHeader().setStretchLastSection(True)

        self.history_table.setColumnWidth(0, 70)
        self.history_table.setColumnWidth(1, 200)
        self.history_table.setColumnWidth(2, 120)
        self.history_table.setColumnWidth(3, 90)
        self.history_table.setColumnWidth(4, 90)
        self.history_table.setColumnWidth(5, 100)
        # Overall Status column (idx 6) will take remaining space or can be set explicitly
        layout.addWidget(self.history_table)

        # Analytics Table
        analytics_title_label = QLabel("Stock Level Analytics")
        analytics_title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(analytics_title_label)

        self.analytics_table = QTableWidget()
        self.analytics_table.setColumnCount(5)
        self.analytics_table.setHorizontalHeaderLabels([
            "Material ID", "Material Name", "Avg. Lead Time (Days)",
            "Avg. Order Qty", "Orders (Last 90d)"
        ])
        self.analytics_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.analytics_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.analytics_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.analytics_table.verticalHeader().setVisible(False)
        self.analytics_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.analytics_table.horizontalHeader().setStretchLastSection(True)

        self.analytics_table.setColumnWidth(0, 80)  # Material ID
        self.analytics_table.setColumnWidth(1, 250) # Material Name
        self.analytics_table.setColumnWidth(2, 150) # Avg Lead Time
        self.analytics_table.setColumnWidth(3, 120) # Avg Order Qty
        # Orders (Last 90d) column (idx 4) can take remaining space

        layout.addWidget(self.analytics_table)
    
    def setup_connections(self):
        """Set up signal-slot connections."""
        self.refresh_btn.clicked.connect(self.refresh_all_views) # Changed
        # self.process_btn.clicked.connect(self.process_checkins) # Removed
    
    def refresh_all_views(self):
        self.load_pending_orders()
        self.load_order_history()
        self.load_analytics_data() # New call

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
                self.refresh_all_views() # Refresh both tables in this widget
                self.data_changed.emit() # Notify MainWindow
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
                self.refresh_all_views() # Refresh both tables in this widget
                self.data_changed.emit() # Notify MainWindow
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

    def load_order_history(self):
        try:
            self.history_table.setRowCount(0)
            conn = db.get_connection()
            cursor = conn.cursor()

            # Query to get order details, material name, and total received quantity
            cursor.execute('''
                SELECT
                    o.id,
                    m.name AS material_name,
                    o.order_date,
                    o.order_qty,
                    o.is_processed,
                    COALESCE(SUM(r.received_qty), 0) AS total_received_qty
                FROM orders o
                JOIN materials m ON o.material_id = m.id
                LEFT JOIN receipts r ON o.id = r.order_id
                GROUP BY o.id, m.name, o.order_date, o.order_qty, o.is_processed
                ORDER BY o.order_date DESC, o.id DESC
            ''')
            history_orders = cursor.fetchall()
            conn.close()

            for row_idx, order_data in enumerate(history_orders):
                self.history_table.insertRow(row_idx)

                order_id = order_data[0]
                material_name = order_data[1]
                order_date_str = str(order_data[2])
                ordered_qty = float(order_data[3])
                is_processed = order_data[4] == 1
                total_received = float(order_data[5])

                # Determine Overall Status
                overall_status = ""
                if total_received >= ordered_qty:
                    overall_status = "Fully Received"
                elif is_processed and total_received < ordered_qty and total_received > 0 :
                    overall_status = "Partially Received"
                elif is_processed and total_received == 0:
                    overall_status = "Processed (No Receipts)"
                elif not is_processed:
                    overall_status = "Pending Processing"
                else:
                    overall_status = "Unknown"

                self.history_table.setItem(row_idx, 0, QTableWidgetItem(str(order_id)))
                self.history_table.setItem(row_idx, 1, QTableWidgetItem(material_name))
                self.history_table.setItem(row_idx, 2, QTableWidgetItem(order_date_str.split(" ")[0]))
                self.history_table.setItem(row_idx, 3, QTableWidgetItem(f"{ordered_qty:.2f}"))
                self.history_table.setItem(row_idx, 4, QTableWidgetItem("Yes" if is_processed else "No"))
                self.history_table.setItem(row_idx, 5, QTableWidgetItem(f"{total_received:.2f}"))
                self.history_table.setItem(row_idx, 6, QTableWidgetItem(overall_status))

            logger.debug(f"Loaded {len(history_orders)} orders into history view.")
        except Exception as e:
            logger.error(f"Failed to load order history: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load order history: {str(e)}")

    def load_analytics_data(self):
        try:
            self.analytics_table.setRowCount(0)

            # Fetch raw analytics data
            avg_lead_times = calculate_average_lead_time_per_material()
            avg_order_qtys = calculate_average_order_quantity_per_material()
            recent_order_counts = count_recent_orders_per_material(days=90)

            # Need material names. Get all materials first.
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM materials ORDER BY id")
            materials_data = cursor.fetchall()
            conn.close()

            all_material_ids = set(m[0] for m in materials_data)
            # Combine all known material IDs from analytics functions as well,
            # in case a material exists in orders/receipts but not in materials table (data integrity issue)
            all_material_ids.update(avg_lead_times.keys())
            all_material_ids.update(avg_order_qtys.keys())
            all_material_ids.update(recent_order_counts.keys())

            material_info_map = {m[0]: m[1] for m in materials_data}

            row_idx = 0
            for material_id in sorted(list(all_material_ids)):
                material_name = material_info_map.get(material_id, f"Unknown ID: {material_id}")

                lead_time_val = avg_lead_times.get(material_id)
                lead_time_str = f"{lead_time_val:.2f}" if lead_time_val is not None else "N/A"

                order_qty_val = avg_order_qtys.get(material_id)
                order_qty_str = f"{order_qty_val:.2f}" if order_qty_val is not None else "N/A"

                recent_count_str = str(recent_order_counts.get(material_id, 0))

                self.analytics_table.insertRow(row_idx)
                self.analytics_table.setItem(row_idx, 0, QTableWidgetItem(str(material_id)))
                self.analytics_table.setItem(row_idx, 1, QTableWidgetItem(material_name))
                self.analytics_table.setItem(row_idx, 2, QTableWidgetItem(lead_time_str))
                self.analytics_table.setItem(row_idx, 3, QTableWidgetItem(order_qty_str))
                self.analytics_table.setItem(row_idx, 4, QTableWidgetItem(recent_count_str))
                row_idx += 1

            logger.debug(f"Loaded analytics data for {row_idx} materials.")
        except Exception as e:
            logger.error(f"Failed to load analytics data: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load analytics data: {str(e)}")
