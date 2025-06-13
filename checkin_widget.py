import logging
import traceback
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                            QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
                            QAbstractItemView, QLabel, QComboBox, QLineEdit, QDateEdit, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QDoubleValidator

from database import db

# Set up logger
logger = logging.getLogger('procurement.checkin')

class CheckInWidget(QWidget):
    """Widget for managing order check-ins and updating inventory."""
    
    # Signal emitted when check-ins are processed
    checkins_processed = pyqtSignal()
    
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
        
        self.title_label = QLabel("Pending Orders for Check-In")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.refresh_btn = QPushButton("Refresh")
        self.process_btn = QPushButton("Process Check-Ins")
        self.process_btn.setEnabled(False)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(self.process_btn)
        
        # Table setup
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "", "Order ID", "Material", "Type", "Supplier", "Ordered Qty",
            "Received Qty", "Status", "Date Received", "Notes"
        ])
        
        # Configure table properties
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        
        # Set column widths
        self.table.setColumnWidth(0, 30)    # Checkbox
        self.table.setColumnWidth(1, 70)    # Order ID
        self.table.setColumnWidth(2, 200)   # Material
        self.table.setColumnWidth(3, 100)   # Type
        self.table.setColumnWidth(4, 150)   # Supplier
        self.table.setColumnWidth(5, 90)    # Ordered Qty
        self.table.setColumnWidth(6, 100)   # Received Qty (editable)
        self.table.setColumnWidth(7, 100)   # Status (dropdown)
        self.table.setColumnWidth(8, 100)   # Date Received
        
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
        self.process_btn.clicked.connect(self.process_checkins)
    
    def load_pending_orders(self):
        """Load orders that are pending or partially received."""
        try:
            # Clear existing data
            self.table.setRowCount(0)
            
            # Get pending orders with material details
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT o.id, m.name, m.type, m.supplier, o.quantity_ordered,
                       o.status, o.order_date, m.id as material_id
                FROM orders o
                JOIN materials m ON o.material_id = m.id
                WHERE o.status IN ('Pending', 'Partially Received')
                ORDER BY o.order_date
            ''')
            
            orders = cursor.fetchall()
            
            # Populate table
            for row, order in enumerate(orders):
                self.table.insertRow(row)
                
                # Add checkbox
                checkbox = QCheckBox()
                checkbox.stateChanged.connect(self.update_process_button_state)
                
                cell_widget = QWidget()
                layout = QHBoxLayout(cell_widget)
                layout.addWidget(checkbox)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                cell_widget.setLayout(layout)
                
                self.table.setCellWidget(row, 0, cell_widget)
                
                # Add order data
                self.table.setItem(row, 1, QTableWidgetItem(str(order[0])))  # Order ID
                self.table.setItem(row, 2, QTableWidgetItem(order[1]))  # Material
                self.table.setItem(row, 3, QTableWidgetItem(order[2]))  # Type
                self.table.setItem(row, 4, QTableWidgetItem(order[3] or ""))  # Supplier
                self.table.setItem(row, 5, QTableWidgetItem(f"{order[4]:.2f}"))  # Ordered Qty
                
                # Received Qty (editable)
                received_qty_edit = QLineEdit("0.00")
                received_qty_edit.setValidator(QDoubleValidator(0, 999999, 2, self))
                received_qty_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
                self.table.setCellWidget(row, 6, received_qty_edit)
                
                # Status (dropdown)
                status_combo = QComboBox()
                status_combo.addItems(["Pending", "Partially Received", "Fully Received", "Incorrect"])
                status_combo.setCurrentText(order[5])
                self.table.setCellWidget(row, 7, status_combo)
                
                # Date Received
                date_edit = QDateEdit()
                date_edit.setCalendarPopup(True)
                date_edit.setDate(QDate.currentDate())
                date_edit.setDisplayFormat("yyyy-MM-dd")
                self.table.setCellWidget(row, 8, date_edit)
                
                # Notes
                notes_edit = QLineEdit()
                notes_edit.setPlaceholderText("Enter any notes...")
                self.table.setCellWidget(row, 9, notes_edit)
                
                # Store material ID as item data
                self.table.item(row, 1).setData(Qt.ItemDataRole.UserRole, order[7])
            
            # Update status
            self.status_label.setText(f"Found {len(orders)} pending orders.")
            
            # Update process button state
            self.update_process_button_state()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load pending orders: {str(e)}")
    
    def update_process_button_state(self):
        """Enable/disable the Process Check-Ins button based on selection."""
        has_selection = False
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                has_selection = True
                break
        
        self.process_btn.setEnabled(has_selection)
    
    def process_checkins(self):
        """Process the selected check-ins and update inventory."""
        conn = None
        try:
            logger.info("Starting process_checkins")
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Get selected rows
            selected_rows = []
            logger.debug(f"Checking {self.table.rowCount()} rows for checkboxes")
            
            for row in range(self.table.rowCount()):
                try:
                    checkbox_widget = self.table.cellWidget(row, 0)
                    if not checkbox_widget:
                        logger.warning(f"No widget at row {row}, column 0")
                        continue
                        
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if not checkbox:
                        logger.warning(f"No QCheckBox found at row {row}")
                        continue
                        
                    if checkbox.isChecked():
                        logger.debug(f"Found checked row: {row}")
                        selected_rows.append(row)
                except Exception as e:
                    logger.error(f"Error processing row {row}: {str(e)}", exc_info=True)
            
            if not selected_rows:
                logger.warning("No rows selected for processing")
                QMessageBox.warning(self, "No Selection", "Please select at least one order to process.")
                return
                
            logger.info(f"Selected {len(selected_rows)} rows for processing: {selected_rows}")
            
            # Confirm before processing
            reply = QMessageBox.question(
                self,
                "Confirm Check-Ins",
                f"Process check-ins for {len(selected_rows)} order(s)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                logger.info("User cancelled check-in processing")
                return
            
            # Process each selected order
            success_count = 0
            for row in selected_rows:
                try:
                    logger.debug(f"\nProcessing row {row}")
                    
                    # Get order ID and material ID
                    item = self.table.item(row, 1)
                    if not item:
                        logger.error(f"No item at row {row}, column 1")
                        continue
                        
                    order_id = int(item.text())
                    material_id = item.data(Qt.ItemDataRole.UserRole)
                    
                    # Get ordered quantity
                    ordered_qty_item = self.table.item(row, 5)
                    if not ordered_qty_item:
                        logger.error(f"No ordered quantity at row {row}, column 5")
                        continue
                        
                    ordered_qty = float(ordered_qty_item.text())
                    logger.debug(f"Order ID: {order_id}, Material ID: {material_id}, Ordered Qty: {ordered_qty}")
                    
                    # Get values from form
                    received_qty_edit = self.table.cellWidget(row, 6)
                    status_combo = self.table.cellWidget(row, 7)
                    date_edit = self.table.cellWidget(row, 8)
                    notes_edit = self.table.cellWidget(row, 9)
                    
                    if not all([received_qty_edit, status_combo, date_edit, notes_edit]):
                        logger.error(f"Missing widget(s) in row {row}")
                        continue
                    
                    received_qty = float(received_qty_edit.text() or "0")
                    status = status_combo.currentText()
                    received_date = date_edit.date().toString("yyyy-MM-dd")
                    notes = notes_edit.text()
                    
                    logger.info(f"Processing: Order {order_id}, Qty: {received_qty}, Status: {status}")
                    
                    # Start a savepoint for this order
                    savepoint = f"sp_{order_id}"
                    cursor.execute(f"SAVEPOINT {savepoint}")
                    
                    try:
                        # Record check-in
                        cursor.execute('''
                            INSERT INTO checkins (order_id, received_qty, status, notes, checkin_date)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (order_id, received_qty, status, notes, received_date))
                        logger.debug(f"Inserted checkin record for order {order_id}")
                        
                        # Update order status
                        cursor.execute('''
                            UPDATE orders SET status = ?
                            WHERE id = ?
                        ''', (status, order_id))
                        logger.debug(f"Updated order {order_id} status to {status}")
                        
                        # Update inventory if received
                        if received_qty > 0 and status in ["Partially Received", "Fully Received"]:
                            cursor.execute('''
                                UPDATE materials 
                                SET current_qty = current_qty + ?
                                WHERE id = ?
                            ''', (received_qty, material_id))
                            logger.debug(f"Updated material {material_id} quantity by {received_qty}")
                        
                        # Release savepoint on success
                        cursor.execute(f"RELEASE SAVEPOINT {savepoint}")
                        success_count += 1
                        
                    except Exception as e:
                        # Rollback to savepoint on error
                        cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                        logger.error(f"Error processing order {order_id}: {str(e)}", exc_info=True)
                        QMessageBox.warning(
                            self, 
                            "Processing Error",
                            f"Error processing order {order_id}:\n{str(e)}\n\nSkipping this order.",
                            QMessageBox.StandardButton.Ok
                        )
                
                except Exception as e:
                    logger.error(f"Unexpected error processing row {row}: {str(e)}", exc_info=True)
                    QMessageBox.warning(
                        self,
                        "Processing Error",
                        f"Unexpected error processing row {row + 1}:\n{str(e)}\n\nSkipping this order.",
                        QMessageBox.StandardButton.Ok
                    )
            
            if success_count > 0:
                # Only commit if we had at least one successful operation
                conn.commit()
                logger.info(f"Successfully processed {success_count}/{len(selected_rows)} check-ins")
                
                # Update status and refresh
                self.status_label.setText(f"Successfully processed {success_count} check-in(s).")
                self.checkins_processed.emit()
                
                # Refresh the list
                logger.debug("Refreshing pending orders list")
                self.load_pending_orders()
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Check-Ins Processed",
                    f"Successfully processed {success_count} out of {len(selected_rows)} check-in(s).",
                    QMessageBox.StandardButton.Ok
                )
            else:
                conn.rollback()
                logger.warning("No check-ins were processed successfully")
                QMessageBox.warning(
                    self,
                    "No Check-Ins Processed",
                    "No check-ins were processed successfully. Please check the logs for errors.",
                    QMessageBox.StandardButton.Ok
                )
            
        except Exception as e:
            error_msg = f"Critical error in process_checkins: {str(e)}"
            logger.critical(error_msg, exc_info=True)
            QMessageBox.critical(
                self, 
                "Critical Error", 
                f"A critical error occurred while processing check-ins:\n{str(e)}\n\nPlease check the logs for details.",
                QMessageBox.StandardButton.Ok
            )
            if conn:
                conn.rollback()
                logger.info("Database changes rolled back due to error")
        finally:
            # Ensure the connection is closed
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing database connection: {str(e)}", exc_info=True)
