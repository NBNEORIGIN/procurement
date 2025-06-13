from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                            QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
                            QAbstractItemView, QLineEdit, QLabel, QComboBox, QSizePolicy,
                            QMenu) # Added QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QAction, QIcon, QKeySequence, QColor # Added QKeySequence, QColor
import logging # Added logging

from database import db

logger = logging.getLogger('procurement.materials_list') # Setup logger

class MaterialsListWidget(QWidget):
    """Widget to display and manage a list of materials."""
    
    # Signal emitted when a material is selected for editing
    edit_requested = pyqtSignal(dict)
    add_new_requested = pyqtSignal()
    # duplicate_requested = pyqtSignal(dict) # Reusing edit_requested for duplicate
    
    def __init__(self):
        super().__init__()
        self._item_changed_guard = False # Initialize guard for itemChanged signal
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
        self.table.setColumnCount(8) # Actions column removed
        self.table.setHorizontalHeaderLabels([
            "ID", "Type", "Name", "Unit", "Current Stock", "Min Stock",
            "Supplier", "Order URL" # Actions removed
        ])
        
        # Configure table properties
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # Allow editing
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked |
            QTableWidget.EditTrigger.SelectedClicked |
            QTableWidget.EditTrigger.EditKeyPressed
        )
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu) # Enable context menu
        
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
        self.table.itemChanged.connect(self.handle_item_changed) # Connect itemChanged
        self.table.customContextMenuRequested.connect(self.show_table_context_menu) # Connect context menu
    
    def load_materials(self):
        """Load materials from the database and populate the table."""
        self._item_changed_guard = True # Guard during loading
        try:
            # Clear existing data
            self.table.setRowCount(0)
            
            # Get materials from database
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials ORDER BY type, name")
            materials = cursor.fetchall()
            conn.close() # Close connection after fetching
            
            # Update type filter
            self.update_type_filter(materials)
            
            # Populate table
            for row, material in enumerate(materials):
                self.table.insertRow(row)
                
                # id:0, type:1, name:2, unit:3, current_stock:4, min_stock:5,
                # reorder_point:6, order_method:7, supplier:8, order_url:9, ...

                id_item = QTableWidgetItem(str(material[0]))
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Make ID non-editable
                self.table.setItem(row, 0, id_item)

                self.table.setItem(row, 1, QTableWidgetItem(material[1]))  # Type
                self.table.setItem(row, 2, QTableWidgetItem(material[2]))  # Name
                self.table.setItem(row, 3, QTableWidgetItem(material[3]))  # Unit
                self.table.setItem(row, 4, QTableWidgetItem(str(material[4])))  # Current Stock
                self.table.setItem(row, 5, QTableWidgetItem(str(material[5])))  # Min Stock
                self.table.setItem(row, 6, QTableWidgetItem(material[8] or ""))  # Supplier
                self.table.setItem(row, 7, QTableWidgetItem(material[9] or ""))  # Order URL
                
                # Action buttons column removed
            
            # Resize columns to contents
            self.table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"Failed to load materials: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load materials: {str(e)}")
        finally:
            self._item_changed_guard = False # Release guard

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
            should_show = True # Corrected: assume should_show is true initially
            
            # Apply type filter
            if filter_type != "all":
                type_item = self.table.item(row, 1)  # Type column
                if not type_item or type_item.text() != filter_type: # Check if item exists
                    should_show = False
            
            # Apply search filter
            if should_show and search_text: # Only search if still visible
                row_matches = False
                # Now columnCount is 8, so loop up to 7 (0 to 7)
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        row_matches = True
                        break
                if not row_matches: # If no match in any relevant column
                    should_show = False
            
            # Show/hide row
            self.table.setRowHidden(row, not should_show)
    
    # on_edit_clicked and on_delete_clicked are removed as buttons are gone.
    # Context menu and itemChanged signal handle these actions now.

    def edit_material(self, material_id):
        """Emit signal to edit the selected material using the full form."""
        # This method is now primarily called from the context menu's "Edit Full Details..."
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
            material = cursor.fetchone()
            conn.close()
            
            if material:
                material_dict = {
                    'id': material[0], 'type': material[1], 'name': material[2],
                    'unit': material[3], 'current_stock': material[4], 'min_stock': material[5],
                    'reorder_point': material[6], 'order_method': material[7],
                    'supplier': material[8], 'order_url': material[9], 'contact': material[10],
                    'notes': material[11]
                    # Add created_at, updated_at if needed by MaterialEntryWidget, though usually not shown for edit
                }
                self.edit_requested.emit(material_dict)
            else:
                QMessageBox.warning(self, "Not Found", f"Material with ID {material_id} not found.")
                
        except Exception as e:
            logger.error(f"Failed to fetch material for editing (ID: {material_id}): {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to fetch material details: {str(e)}")
    
    def delete_material(self, material_id):
        """Delete the selected material from the database."""
        # Confirmation dialog
        reply = QMessageBox.question(
            self, 'Delete Material',
            f'Are you sure you want to delete material ID {material_id}?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Check for dependent records (orders)
            cursor.execute("SELECT COUNT(*) FROM orders WHERE material_id = ?", (material_id,))
            order_count = cursor.fetchone()[0]

            if order_count > 0:
                QMessageBox.warning(
                    self, "Cannot Delete",
                    f"Material ID {material_id} has {order_count} associated order(s) and cannot be deleted."
                )
                conn.close()
                return
            
            # Delete the material
            cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            conn.commit()
            conn.close()
            
            logger.info(f"Successfully deleted material ID {material_id}")
            self.load_materials() # Refresh the table
            
        except Exception as e:
            logger.error(f"Failed to delete material ID {material_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to delete material: {str(e)}")

    def handle_item_changed(self, item):
        if not hasattr(self, '_item_changed_guard') or self._item_changed_guard: # Guard to prevent recursion or during load
            return

        self._item_changed_guard = True # Enter guard

        row = item.row()
        col = item.column()
        new_value = item.text()

        material_id_item = self.table.item(row, 0) # ID is in column 0
        if not material_id_item:
            logger.error(f"Could not find material ID for changed item at row {row}")
            self._item_changed_guard = False
            return

        try:
            material_id = int(material_id_item.text())

            column_map = {
                1: ('type', str), 2: ('name', str), 3: ('unit', str),
                4: ('current_stock', float), 5: ('min_stock', float),
                6: ('supplier', str), 7: ('order_url', str)
            }

            if col not in column_map:
                # logger.debug(f"Column {col} is not directly editable or mapped.")
                self._item_changed_guard = False
                return

            db_column_name, data_type = column_map[col]
            original_value = None # Store original value to revert on validation failure if needed

            # Fetch original value for revert (optional, self.load_materials() is simpler)
            # conn_temp = db.get_connection()
            # cursor_temp = conn_temp.cursor()
            # cursor_temp.execute(f"SELECT {db_column_name} FROM materials WHERE id = ?", (material_id,))
            # original_row = cursor_temp.fetchone()
            # if original_row:
            #     original_value = original_row[0]
            # conn_temp.close()


            validated_value = None
            if data_type == float:
                try:
                    validated_value = float(new_value)
                    if validated_value < 0:
                         raise ValueError("Numeric values cannot be negative.")
                except ValueError as ve:
                    logger.warning(f"Invalid float value for {db_column_name} (ID: {material_id}): {new_value}. Error: {ve}")
                    QMessageBox.warning(self, "Input Error", f"Invalid value for '{self.table.horizontalHeaderItem(col).text()}': '{new_value}'. Must be a non-negative number.")
                    self.load_materials() # Revert by reloading all
                    self._item_changed_guard = False
                    return
            elif data_type == str:
                validated_value = new_value.strip()
                if db_column_name in ['type', 'name', 'unit'] and not validated_value: # Mandatory fields
                    logger.warning(f"Empty value for mandatory field {db_column_name} (ID: {material_id})")
                    QMessageBox.warning(self, "Input Error", f"'{self.table.horizontalHeaderItem(col).text()}' cannot be empty.")
                    self.load_materials() # Revert by reloading all
                    self._item_changed_guard = False
                    return

            conn = db.get_connection()
            cursor = conn.cursor()
            sql = f"UPDATE materials SET {db_column_name} = ? WHERE id = ?"
            cursor.execute(sql, (validated_value, material_id))
            conn.commit()
            conn.close()

            logger.info(f"Material ID {material_id}: Updated {db_column_name} to '{validated_value}' from '{new_value}' (raw cell text)")
            # item.setBackground(QColor("lightgreen")) # Visual feedback (temporary)

        except Exception as e:
            logger.error(f"Error updating material ID {material_id} column {col} ('{db_column_name}') to '{new_value}': {e}", exc_info=True)
            QMessageBox.critical(self, "Update Failed", f"Could not update material: {str(e)}")
            self.load_materials() # Revert changes on error by reloading
        finally:
            self._item_changed_guard = False # Exit guard

    def show_table_context_menu(self, position):
        menu = QMenu(self) # Pass self to ensure proper parenting
        selected_items = self.table.selectedItems()

        if not selected_items:
            return

        selected_row = self.table.row(selected_items[0])
        material_id_item = self.table.item(selected_row, 0)

        if not material_id_item:
            return

        try:
            material_id = int(material_id_item.text())
        except ValueError:
            logger.error(f"Invalid material ID '{material_id_item.text()}' in context menu for row {selected_row}")
            # Still show the "Add New" action
            pass # Fall through to show menu with just "Add New" if no valid row selected for other actions

        # Actions requiring a selected row (and valid material_id)
        if material_id is not None: # material_id would be None if try-except failed or no selection
            menu.addSeparator()
            edit_action = QAction("Edit Full Details...", self)
            edit_action.triggered.connect(lambda id=material_id: self.edit_material(id))
            menu.addAction(edit_action)

            duplicate_action = QAction("Duplicate Selected Material...", self)
            duplicate_action.triggered.connect(lambda id=material_id: self.handle_duplicate_material_action(id))
            menu.addAction(duplicate_action)

            delete_action = QAction("Delete Material", self)
            delete_action.triggered.connect(lambda id=material_id: self.handle_delete_action(id))
            menu.addAction(delete_action)

        menu.exec(self.table.viewport().mapToGlobal(position))

    def handle_delete_action(self, material_id):
        self.delete_material(material_id)

    def handle_add_new_material_action(self):
        logger.info("Add new material requested from context menu.")
        self.add_new_requested.emit()

    def handle_duplicate_material_action(self, material_id):
        logger.info(f"Duplicate material requested for ID: {material_id}")
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
            material = cursor.fetchone()
            conn.close()

            if material:
                material_dict = {
                    'id': None, # Crucial: ID is None for a new entry
                    'type': material[1],
                    'name': material[2] + " (Copy)", # Suggest it's a copy
                    'unit': material[3],
                    'current_stock': material[4], # Or reset to 0. Kept for now.
                    'min_stock': material[5],
                    'reorder_point': material[6],
                    'order_method': material[7],
                    'supplier': material[8],
                    'order_url': material[9],
                    'contact': material[10],
                    'notes': material[11]
                }
                self.edit_requested.emit(material_dict)
            else:
                QMessageBox.warning(self, "Not Found", f"Material with ID {material_id} not found for duplication.")
        except Exception as e:
            logger.error(f"Failed to fetch material for duplication (ID: {material_id}): {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to fetch material details for duplication: {str(e)}")
