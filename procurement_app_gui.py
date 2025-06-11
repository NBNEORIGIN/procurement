import sys
import os
import io
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QLineEdit, QPushButton, QLabel, QFormLayout,
    QMessageBox, QComboBox, QSpinBox, QTextEdit, QHeaderView, QDoubleSpinBox,
    QGroupBox, QCheckBox, QMenu, QStatusBar, QAbstractItemView, QSplitter
)
from PyQt6.QtCore import Qt, QUrl, QObject, pyqtSignal, pyqtSlot, QMutex, QMetaObject, Q_ARG
from PyQt6.QtGui import QDesktopServices, QIntValidator

class QTextEditLogger(QObject):
    def __init__(self, text_edit):
        print("Initializing QTextEditLogger...")  # Debug print
        try:
            super().__init__()
            print("  - QObject initialized")
            
            if not text_edit:
                raise ValueError("TextEdit widget cannot be None")
                
            self.text_edit = text_edit
            self.buffer = ''
            self._mutex = QMutex()
            print("  - Instance variables initialized")
            print("QTextEditLogger initialized successfully")  # Debug print
        except Exception as e:
            print(f"  - ERROR in QTextEditLogger.__init__: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        
    def write(self, message):
        try:
            if not message or not hasattr(self, 'text_edit') or not self.text_edit:
                return
                
            # Ensure we're working with a string
            if not isinstance(message, str):
                message = str(message)
                
            self._mutex.lock()
            try:
                self.buffer += message
                if '\n' in self.buffer:
                    lines = self.buffer.split('\n')
                    for line in lines[:-1]:
                        if line:  # Don't append empty lines
                            self.text_append(line)
                    self.buffer = lines[-1]
            finally:
                self._mutex.unlock()
        except Exception as e:
            print(f"Error in QTextEditLogger.write: {e}")
    
    def flush(self):
        try:
            self._mutex.lock()
            if self.buffer and hasattr(self, 'text_edit') and self.text_edit:
                self.text_append(self.buffer)
                self.buffer = ''
        except Exception as e:
            print(f"Error in QTextEditLogger.flush: {e}")
        finally:
            self._mutex.unlock()
    
    def text_append(self, text):
        try:
            if not hasattr(self, 'text_edit') or not self.text_edit:
                return
                
            # Use a queued connection to ensure thread safety
            QMetaObject.invokeMethod(self.text_edit, 'append', 
                                   Qt.ConnectionType.QueuedConnection,
                                   Q_ARG(str, text))
                                   
            # Scroll to bottom
            scroll_bar = self.text_edit.verticalScrollBar()
            if scroll_bar:
                QMetaObject.invokeMethod(scroll_bar, 'setValue',
                                       Qt.ConnectionType.QueuedConnection,
                                       Q_ARG(int, scroll_bar.maximum()))
        except Exception as e:
            print(f"Error in text_append: {e}")

class DebugConsole(QWidget):
    def __init__(self, parent=None):
        print("  - Initializing DebugConsole...")
        try:
            super().__init__(parent)
            print("    - Parent initialized")
            
            # Create layout
            self.layout = QVBoxLayout()
            self.setLayout(self.layout)
            print("    - Layout created")
            
            # Create a text edit for debug output
            print("    - Creating debug output widget...")
            self.debug_output = QTextEdit()
            self.debug_output.setReadOnly(True)
            print("    - Debug output widget created")
            
            # Set style sheet
            try:
                print("    - Setting stylesheet...")
                self.debug_output.setStyleSheet("""
                    QTextEdit {
                        background-color: #1e1e1e;
                        color: #f0f0f0;
                        font-family: Consolas, 'Courier New', monospace;
                        font-size: 10pt;
                        border: 1px solid #444;
                        border-radius: 4px;
                        padding: 4px;
                    }
                """)
                print("    - Stylesheet set")
            except Exception as e:
                print(f"    - WARNING: Could not set stylesheet: {e}")
            
            # Create clear button
            print("    - Creating clear button...")
            clear_btn = QPushButton("Clear Console")
            clear_btn.clicked.connect(self.debug_output.clear)
            print("    - Clear button created and connected")
            
            # Add widgets to layout
            print("    - Adding widgets to layout...")
            self.layout.addWidget(QLabel("Debug Console"))
            self.layout.addWidget(self.debug_output)
            self.layout.addWidget(clear_btn)
            print("    - Widgets added to layout")
            
            # Redirect stdout and stderr to our console
            print("    - Setting up stdout/stderr redirection...")
            try:
                # Save original stdout/stderr
                self.original_stdout = sys.stdout
                self.original_stderr = sys.stderr
                
                # Create and set up logger
                self.logger = QTextEditLogger(self.debug_output)
                sys.stdout = self.logger
                sys.stderr = self.logger
                
                # Test the logger
                print("    - Testing debug console output...")
                print("    - Stdout/stderr redirection complete")
                print("  - DebugConsole initialization complete")
                
            except Exception as e:
                print(f"    - ERROR setting up stdout/stderr redirection: {str(e)}")
                import traceback
                traceback.print_exc()
                # Restore original stdout/stderr on error
                sys.stdout = self.original_stdout
                sys.stderr = self.original_stderr
                raise
            
        except Exception as e:
            error_msg = f"ERROR in DebugConsole.__init__: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            raise
            
    def closeEvent(self, event):
        # Restore original stdout/stderr when closing
        if hasattr(self, 'original_stdout'):
            sys.stdout = self.original_stdout
        if hasattr(self, 'original_stderr'):
            sys.stderr = self.original_stderr
        event.accept()
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QLineEdit, QPushButton, QLabel, QFormLayout,
    QMessageBox, QComboBox, QSpinBox, QTextEdit, QHeaderView, QDoubleSpinBox,
    QGroupBox, QCheckBox, QMenu, QStatusBar, QAbstractItemView, QSplitter
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIntValidator
import os
from datetime import datetime
from main import (append_to_csv, main as generate_orders_main_logic,
                  process_single_purchase_order, log_order_to_history,
                  SUPPLIERS_FILE, SUPPLIERS_HEADERS) # Added new imports

def generate_order_id():
    return f"PO-{datetime.now().strftime('%Y%m%d-%H%M%S%f')[:-3]}"

# File paths
MATERIALS_FILE = "materials_master.csv"
SUPPLIERS_FILE = "suppliers.csv"
ORDER_HISTORY_FILE = "order_history.csv"
MATERIALS_RECEIVED_FILE = "materials_received.csv"

# Column headers for data files
MATERIALS_HEADERS = ['MaterialID', 'MaterialName', 'Category', 'UnitOfMeasure', 'CurrentStock',
                   'ReorderPoint', 'StandardOrderQuantity', 'PreferredSupplierID',
                   'ProductPageURL', 'LeadTimeDays', 'SafetyStockQuantity', 'Notes', 'CurrentPrice']

SUPPLIERS_HEADERS = ['SupplierID', 'SupplierName', 'ContactPerson', 'Email', 'Phone', 'Website', 'OrderMethod']

ORDER_HISTORY_HEADERS = ['OrderID', 'Timestamp', 'MaterialID', 'MaterialName', 'QuantityOrdered',
                       'UnitPricePaid', 'TotalPricePaid', 'SupplierID', 'SupplierName',
                       'OrderMethod', 'Status', 'QuantityReceived', 'DateReceived', 'Notes']

MATERIALS_RECEIVED_HEADERS = ORDER_HISTORY_HEADERS

def get_int_val(val_str, default=0):
    try: return int(float(str(val_str))) if pd.notna(val_str) and str(val_str).strip() != '' else default
    except ValueError: return default
def get_float_val(val_str, default=0.0):
    try: return float(str(val_str)) if pd.notna(val_str) and str(val_str).strip() != '' else default
    except ValueError: return default

def load_or_create_dataframe_app(file_path, expected_headers, default_dtype=str, parent_widget=None, create_if_missing=False):
    """
    Load a CSV file into a pandas DataFrame, or create it if it doesn't exist.
    
    Args:
        file_path (str): Path to the CSV file
        expected_headers (list): List of expected column headers
        default_dtype: Default data type for columns
        parent_widget: Optional parent widget for error dialogs
        create_if_missing (bool): Whether to create the file if it doesn't exist
        
    Returns:
        pandas.DataFrame: Loaded or created DataFrame with expected columns
    """
    def show_error_dialog(message, details=None):
        """Show an error dialog if parent_widget is provided, otherwise print to console"""
        if parent_widget:
            error_dialog = QMessageBox(parent_widget)
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Data Loading Error")
            error_dialog.setText(message)
            if details:
                error_dialog.setDetailedText(details)
            error_dialog.exec()
        else:
            print(f"Error: {message}")
            if details:
                print(f"Details: {details}")
    
    # Validate file path
    if not isinstance(file_path, str) or not file_path.strip():
        show_error_dialog("Invalid file path provided")
        return pd.DataFrame(columns=expected_headers).astype(default_dtype).fillna('')
    
    # Handle existing file
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            # Read the file with error handling for encoding issues
            try:
                df = pd.read_csv(file_path, dtype=str).fillna('')
            except UnicodeDecodeError:
                # Try different encodings if UTF-8 fails
                for encoding in ['utf-8', 'latin1', 'cp1252']:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, dtype=str).fillna('')
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError(f"Could not read {file_path} with any standard encoding")
            
            current_headers = df.columns.tolist()
            missing_cols_exist = False
            
            # Special handling for order history file
            if file_path == ORDER_HISTORY_FILE:
                if 'QuantityReceived' not in current_headers:
                    df['QuantityReceived'] = '0'
                    current_headers.append('QuantityReceived')
                    missing_cols_exist = True
                else:
                    df['QuantityReceived'] = df['QuantityReceived'].replace('', '0').fillna('0')
                
                if 'DateReceived' not in current_headers:
                    df['DateReceived'] = ''
                    current_headers.append('DateReceived')
                    missing_cols_exist = True
            
            # Ensure all expected headers exist
            for header in expected_headers:
                if header not in current_headers:
                    df[header] = ''
                    missing_cols_exist = True
            
            # Log schema changes if any
            if missing_cols_exist:
                timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                log_entry = f"[{timestamp_str}] TITLE: File Schema Notice MESSAGE: File '{file_path}' had schema issues; defaults applied and aligned."
                try:
                    with open("popup_messages.txt", "a", encoding="utf-8") as f_popup_log:
                        f_popup_log.write(log_entry + "\n")
                except Exception as e_popup:
                    print(f"Failed to write to popup_messages.txt: {e_popup}")
            
            # Ensure all expected columns exist and in correct order
            df = df.reindex(columns=expected_headers, fill_value='')
            
            # Special handling for numeric fields in order history
            if file_path == ORDER_HISTORY_FILE:
                numeric_cols = ['QuantityOrdered', 'UnitPricePaid', 'TotalPricePaid', 'QuantityReceived']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                        if default_dtype == str:
                            df[col] = df[col].astype(str)
            
            return df[expected_headers].fillna('')
            
        except Exception as e:
            error_msg = f"Failed to load {file_path}"
            error_details = f"Error: {str(e)}\n\nFile: {file_path}"
            show_error_dialog(error_msg, error_details)
            return pd.DataFrame(columns=expected_headers).astype(default_dtype).fillna('')
    
    # Handle missing file with create_if_missing=True
    elif create_if_missing:
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            # Create empty DataFrame with expected columns
            df = pd.DataFrame(columns=expected_headers)
            df.to_csv(file_path, index=False)
            
            # Log the creation of a new file
            timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            log_entry = f"[{timestamp_str}] Created new file: {file_path}"
            try:
                with open("popup_messages.txt", "a", encoding="utf-8") as f_popup_log:
                    f_popup_log.write(log_entry + "\n")
            except Exception as e_popup:
                print(f"Failed to write to popup_messages.txt: {e_popup}")
                
            return df.astype(default_dtype).fillna('')
            
        except Exception as e:
            error_msg = f"Failed to create {file_path}"
            error_details = f"Error: {str(e)}\n\nPath: {file_path}"
            show_error_dialog(error_msg, error_details)
            return pd.DataFrame(columns=expected_headers).astype(default_dtype).fillna('')
    
    # Return empty DataFrame if file doesn't exist and create_if_missing is False
    else:
        return pd.DataFrame(columns=expected_headers).astype(default_dtype).fillna('')

class DataManagementWidget(QWidget):
    def __init__(self, materials_df, suppliers_df, save_any_dataframe, refresh_preferred_supplier_dropdown_in_materials_tab, parent=None):
        super().__init__(parent)
        self.materials_df = materials_df
        self.suppliers_df = suppliers_df
        self.save_any_dataframe = save_any_dataframe
        self.refresh_preferred_supplier_dropdown_in_materials_tab = refresh_preferred_supplier_dropdown_in_materials_tab
        main_layout = QVBoxLayout(self)
        
        self.setLayout(main_layout)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Setup materials tab
        self.materials_tab = QWidget()
        self.tabs.addTab(self.materials_tab, "Materials")
        materials_tab_layout = QVBoxLayout(self.materials_tab)
        
        # Initialize materials table
        self.materials_table_view = QTableWidget()
        print("Table widget created")
        
        # Set up context menu policy before adding to layout
        print("Setting up context menu policy...")
        self.materials_table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        print(f"Context menu policy set: {self.materials_table_view.contextMenuPolicy()}")
        
        # Connect the custom context menu signal
        print("Connecting context menu signal...")
        self.materials_table_view.customContextMenuRequested.connect(self.show_materials_context_menu)
        print("Context menu signal connected")
        print(f"Debug: customContextMenuRequested signal object: {self.materials_table_view.customContextMenuRequested}")
        # The policy is set before connecting, this confirms it.
        print(f"Debug: ContextMenuPolicy in __init__ (after connect): {self.materials_table_view.contextMenuPolicy().name}")
        self.materials_table_view.setEnabled(True)
        self.materials_table_view.setVisible(True)
        self.materials_table_view.viewport().setEnabled(True)
        self.materials_table_view.viewport().setMouseTracking(True)
        print("Materials table and viewport explicitly enabled, set visible, and mouse tracking on in __init__")
        self.materials_table_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.materials_table_view.viewport().setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.materials_table_view.viewport().setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        print("Debug: Applied FocusPolicy and Viewport Attributes in __init__")

        # --- Start of mousePressEvent debugging code ---
        def new_materials_table_mousePressEvent(widget_instance, event):
            # Print basic event info
            print(f"Debug: materials_table_view.mousePressEvent triggered. Button: {event.button()}, GlobalPos: {event.globalPosition()}")

            # Specifically check for right-click
            if event.button() == Qt.MouseButton.RightButton:
                print(f"Debug: Right-click detected by instance_mousePressEvent on materials_table_view.")
                print(f"  Debug: Table geometry: {widget_instance.geometry()}, isVisible: {widget_instance.isVisible()}")
                print(f"  Debug: Viewport geometry: {widget_instance.viewport().geometry()}, isVisible: {widget_instance.viewport().isVisible()}")
                # Also check custom context menu policy status here again
                print(f"  Debug: Table ContextMenuPolicy at right-click: {widget_instance.contextMenuPolicy().name}")

            # IMPORTANT: Call the original QTableWidget's mousePressEvent
            # This ensures that normal table interactions (like selection) still work.
            QTableWidget.mousePressEvent(widget_instance, event)

        # Dynamically assign this new method to the instance of our table view
        self.materials_table_view.mousePressEvent = new_materials_table_mousePressEvent.__get__(self.materials_table_view)
        print("Debug: Dynamically assigned mousePressEvent to self.materials_table_view for debugging.")
        # --- End of mousePressEvent debugging code ---
        
        # Add table to layout
        materials_tab_layout.addWidget(self.materials_table_view)
        print("Table added to layout")
        
        # Make sure the table is editable
        print("Setting up edit triggers...")
        self.materials_table_view.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | 
            QTableWidget.EditTrigger.EditKeyPressed |
            QTableWidget.EditTrigger.AnyKeyPressed
        )
        print(f"Edit triggers set: {self.materials_table_view.editTriggers()}")
        details_groupbox = QGroupBox("Material Details")
        form_layout = QFormLayout(details_groupbox)
        self.mat_id_edit = QLineEdit(); self.mat_id_edit.setReadOnly(True); form_layout.addRow("MaterialID*:", self.mat_id_edit)
        self.mat_name_edit = QLineEdit(); form_layout.addRow("MaterialName*:", self.mat_name_edit)
        self.mat_cat_edit = QLineEdit(); form_layout.addRow("Category:", self.mat_cat_edit)
        self.mat_uom_edit = QLineEdit(); form_layout.addRow("Unit of Measure:", self.mat_uom_edit)
        self.mat_stock_spin = QSpinBox(); self.mat_stock_spin.setRange(0,999999); form_layout.addRow("Current Stock:", self.mat_stock_spin)
        self.mat_rop_spin = QSpinBox(); self.mat_rop_spin.setRange(0,999999); form_layout.addRow("Reorder Point:", self.mat_rop_spin)
        self.mat_soq_spin = QSpinBox(); self.mat_soq_spin.setRange(0,999999); form_layout.addRow("Std. Order Qty:", self.mat_soq_spin)
        self.mat_price_spin = QDoubleSpinBox(); self.mat_price_spin.setRange(0,99999.99); self.mat_price_spin.setDecimals(2); self.mat_price_spin.setPrefix("£"); form_layout.addRow("Current Price:", self.mat_price_spin)
        self.mat_pref_sup_combo = QComboBox(); form_layout.addRow("Preferred SupplierID:", self.mat_pref_sup_combo)
        self.mat_url_edit = QLineEdit(); form_layout.addRow("Product Page URL:", self.mat_url_edit)
        self.mat_lead_spin = QSpinBox(); self.mat_lead_spin.setRange(0,365); form_layout.addRow("Lead Time (Days):", self.mat_lead_spin)
        self.mat_safe_stock_spin = QSpinBox(); self.mat_safe_stock_spin.setRange(0,999999); form_layout.addRow("Safety Stock Qty:", self.mat_safe_stock_spin)
        self.mat_notes_edit = QTextEdit(); self.mat_notes_edit.setFixedHeight(60); form_layout.addRow("Notes:", self.mat_notes_edit)
        materials_tab_layout.addWidget(details_groupbox)
        buttons_layout = QHBoxLayout(); self.mat_add_btn = QPushButton("Add New Material"); self.mat_save_btn = QPushButton("Save Material"); self.mat_del_btn = QPushButton("Delete Material"); self.mat_clear_btn = QPushButton("Clear Form")
        buttons_layout.addWidget(self.mat_add_btn); buttons_layout.addWidget(self.mat_save_btn); buttons_layout.addWidget(self.mat_del_btn); buttons_layout.addWidget(self.mat_clear_btn)
        materials_tab_layout.addLayout(buttons_layout)
        self.materials_tab.setLayout(materials_tab_layout)
        self.suppliers_tab = QWidget(); self.tabs.addTab(self.suppliers_tab, "Suppliers")
        suppliers_tab_layout = QVBoxLayout(self.suppliers_tab); self.suppliers_table_view = QTableWidget(); suppliers_tab_layout.addWidget(self.suppliers_table_view)
        sup_details_groupbox = QGroupBox("Supplier Details"); sup_form_layout = QFormLayout(sup_details_groupbox)
        self.sup_id_edit = QLineEdit(); self.sup_id_edit.setReadOnly(True); sup_form_layout.addRow("SupplierID*:", self.sup_id_edit)
        self.sup_name_edit = QLineEdit(); sup_form_layout.addRow("SupplierName*:", self.sup_name_edit)
        self.sup_contact_edit = QLineEdit(); sup_form_layout.addRow("Contact Person:", self.sup_contact_edit)
        self.sup_email_edit = QLineEdit(); sup_form_layout.addRow("Email:", self.sup_email_edit)
        self.sup_phone_edit = QLineEdit(); sup_form_layout.addRow("Phone:", self.sup_phone_edit)
        self.sup_website_edit = QLineEdit(); sup_form_layout.addRow("Website:", self.sup_website_edit)
        self.sup_order_method_combo = QComboBox(); self.sup_order_method_combo.addItems(["", "email", "online", "phone", "other"]); sup_form_layout.addRow("Order Method:", self.sup_order_method_combo)
        suppliers_tab_layout.addWidget(sup_details_groupbox)
        sup_buttons_layout = QHBoxLayout(); self.sup_add_btn = QPushButton("Add New Supplier"); self.sup_save_btn = QPushButton("Save Supplier"); self.sup_del_btn = QPushButton("Delete Supplier"); self.sup_clear_btn = QPushButton("Clear Form")
        sup_buttons_layout.addWidget(self.sup_add_btn); sup_buttons_layout.addWidget(self.sup_save_btn); sup_buttons_layout.addWidget(self.sup_del_btn); sup_buttons_layout.addWidget(self.sup_clear_btn)
        suppliers_tab_layout.addLayout(sup_buttons_layout)
        self.suppliers_tab.setLayout(suppliers_tab_layout)
        self.populate_preferred_supplier_dropdown(); self.refresh_materials_table(); self.materials_table_view.itemSelectionChanged.connect(self.on_material_selected); self.mat_clear_btn.clicked.connect(self.clear_material_form)
        self.refresh_suppliers_table(); self.suppliers_table_view.itemSelectionChanged.connect(self.on_supplier_selected); self.sup_clear_btn.clicked.connect(self.clear_supplier_form)
        self.mat_save_btn.clicked.connect(self.save_material_data); self.sup_save_btn.clicked.connect(self.save_supplier_data)
    def populate_preferred_supplier_dropdown(self): # ...
        self.mat_pref_sup_combo.clear(); self.mat_pref_sup_combo.addItem("", None)
        if self.suppliers_df is not None and not self.suppliers_df.empty:
            for index, row in self.suppliers_df.iterrows(): self.mat_pref_sup_combo.addItem(f"{row['SupplierID']} : {row['SupplierName']}", row['SupplierID'])
    def show_materials_context_menu(self, position):
        """Show context menu for materials table"""
        print("\n--- Context menu requested ---")
        print(f"Position: {position}")
        print(f"Debug: Table isVisible: {self.materials_table_view.isVisible()}")
        print(f"Debug: Table isEnabled: {self.materials_table_view.isEnabled()}")
        print(f"Debug: Viewport isVisible: {self.materials_table_view.viewport().isVisible()}")
        print(f"Debug: Viewport isEnabled: {self.materials_table_view.viewport().isEnabled()}")
        try:
            menu = QMenu(self.materials_table_view)
            print(f"Debug: Menu parent: {menu.parent()}")
            print(f"Debug: Menu parent is materials_table_view: {menu.parent() == self.materials_table_view}")
            target_row = self.materials_table_view.rowAt(position.y())
            print(f"Target row for context menu: {target_row}")

            # Add actions
            insert_action = menu.addAction("Insert Row")
            delete_action = menu.addAction("Delete Row")

            # Connect actions
            insert_action.triggered.connect(
                lambda: self.insert_material_row(target_row if target_row != -1 else self.materials_table_view.rowCount())
            )
            delete_action.triggered.connect(self.delete_material_row)

            # If right-click is not on a row, disable delete action
            if target_row == -1:
                delete_action.setEnabled(False)
                print("No row under cursor - delete action disabled")

            # Show the context menu
            print("Showing context menu...")
            menu.popup(self.materials_table_view.viewport().mapToGlobal(position))
            print("Context menu shown")

        except Exception as e:
            error_msg = f"Error in context menu: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)
    
    def insert_material_row(self, position=None):
        """Insert a new row in the materials table at the specified position or at the end"""
        try:
            # If position is None or invalid, append to the end
            if position is None or position < 0 or position > self.materials_table_view.rowCount():
                position = self.materials_table_view.rowCount()
            
            # Insert the new row
            self.materials_table_view.insertRow(position)
            
            # Add empty items to all columns
            for col in range(self.materials_table_view.columnCount()):
                item = QTableWidgetItem("")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.materials_table_view.setItem(position, col, item)
            
            # Select and scroll to the new row
            self.materials_table_view.selectRow(position)
            self.materials_table_view.scrollToItem(self.materials_table_view.item(position, 0))
            
            # Set focus to the first cell of the new row
            if self.materials_table_view.item(position, 0):
                self.materials_table_view.setCurrentCell(position, 0)
            
            # Save changes
            self.save_materials_changes()
            
            # Return the new row index
            return position
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to insert row: {str(e)}")
            return -1
    
    def delete_material_row(self):
        """Delete selected row from materials table"""
        try:
            current_row = self.materials_table_view.currentRow()
            if current_row >= 0:
                reply = QMessageBox.question(
                    self, 'Delete Row',
                    'Are you sure you want to delete this row?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.materials_table_view.removeRow(current_row)
                    self.save_materials_changes()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete row: {str(e)}")
    
    def save_materials_changes(self):
        """Save changes from the table back to the dataframe and CSV"""
        try:
            # Create a new dataframe from the table
            rows = self.materials_table_view.rowCount()
            cols = self.materials_table_view.columnCount()
            
            # Get headers
            headers = []
            for i in range(cols):
                headers.append(self.materials_table_view.horizontalHeaderItem(i).text())
            
            # Get data
            data = []
            for row in range(rows):
                row_data = []
                for col in range(cols):
                    item = self.materials_table_view.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            
            # Update the dataframe
            self.materials_df = pd.DataFrame(data, columns=headers)
            
            # Save to CSV
            self.save_any_dataframe(self.materials_df, 'materials_master.csv')
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {str(e)}")
    
    def refresh_materials_table(self):
        """Refresh the materials table with data from the dataframe"""
        print("\n--- Refreshing materials table ---")
        
        if self.materials_df is None:
            print("Materials dataframe not available for refreshing table.")
            return
            
        print(f"Found {len(self.materials_df)} materials to display")
        
        # Store current scroll position and selection
        scroll_pos = self.materials_table_view.verticalScrollBar().value()
        selected_row = self.materials_table_view.currentRow()
        print(f"Stored scroll position: {scroll_pos}, selected row: {selected_row}")
        
        # Block signals to prevent selection changes during update
        print("Blocking signals during update...")
        self.materials_table_view.blockSignals(True)
        
        try:
            print("Clearing existing table data...")
            self.materials_table_view.clearContents()
            self.materials_table_view.setRowCount(0)
            self.materials_table_view.setColumnCount(len(MATERIALS_HEADERS))
            self.materials_table_view.setHorizontalHeaderLabels(MATERIALS_HEADERS)
            print(f"Set up table with {len(MATERIALS_HEADERS)} columns")
            
            # Set column resize modes
            header = self.materials_table_view.horizontalHeader()
            for i in range(len(MATERIALS_HEADERS)):
                if i in [0, 1, 2, 3]:  # ID, Name, Category, UOM
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
                else:
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            
            # Configure table properties for editing and context menu
            self.materials_table_view.setEditTriggers(
                QTableWidget.EditTrigger.DoubleClicked | 
                QTableWidget.EditTrigger.EditKeyPressed |
                QTableWidget.EditTrigger.AnyKeyPressed
            )
            self.materials_table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            print(f"Debug: ContextMenuPolicy after explicit set in refresh: {self.materials_table_view.contextMenuPolicy().name}")
            self.materials_table_view.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.materials_table_view.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            
            print("Populating table with data...")
            # Populate table
            for r, rd in self.materials_df.iterrows():
                row_position = self.materials_table_view.rowCount()
                self.materials_table_view.insertRow(row_position)
                
                for c, h in enumerate(MATERIALS_HEADERS):
                    item = QTableWidgetItem(str(rd.get(h, '')))
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    self.materials_table_view.setItem(row_position, c, item)
            
            print(f"Added {self.materials_table_view.rowCount()} rows to the table")
            
            # Restore scroll position and selection if possible
            self.materials_table_view.verticalScrollBar().setValue(scroll_pos)
            if 0 <= selected_row < self.materials_table_view.rowCount():
                self.materials_table_view.selectRow(selected_row)
            print(f"Restored scroll position to: {scroll_pos}, selected row: {selected_row}")
            
        except Exception as e:
            print(f"Error refreshing table: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.materials_table_view.setEnabled(True)
            self.materials_table_view.setVisible(True)
            self.materials_table_view.viewport().setEnabled(True)
            self.materials_table_view.viewport().setMouseTracking(True)
            print("Materials table and viewport explicitly enabled, set visible, and mouse tracking on in refresh_materials_table")
            self.materials_table_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.materials_table_view.viewport().setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.materials_table_view.viewport().setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            print("Debug: Re-applied FocusPolicy and Viewport Attributes in refresh_materials_table")
            # Always unblock signals
            print("Unblocking signals...")
            self.materials_table_view.blockSignals(False)
        
        # Ensure the viewport is properly updated
        self.materials_table_view.viewport().update()
        print("Table refresh complete\n")
    def on_material_selected(self): # ...
        si = self.materials_table_view.selectedItems(); sr = self.materials_table_view.currentRow()
        if not si or sr < 0 or sr >= len(self.materials_df): self.clear_material_form(); return
        md = self.materials_df.iloc[sr]; self.mat_id_edit.setText(str(md.get('MaterialID',''))); self.mat_name_edit.setText(str(md.get('MaterialName',''))); self.mat_cat_edit.setText(str(md.get('Category',''))); self.mat_uom_edit.setText(str(md.get('UnitOfMeasure','')))
        self.mat_stock_spin.setValue(get_int_val(md.get('CurrentStock',0))); self.mat_rop_spin.setValue(get_int_val(md.get('ReorderPoint',0))); self.mat_soq_spin.setValue(get_int_val(md.get('StandardOrderQuantity',0))); self.mat_price_spin.setValue(get_float_val(md.get('CurrentPrice',0.0)))
        ci = self.mat_pref_sup_combo.findData(str(md.get('PreferredSupplierID',''))); self.mat_pref_sup_combo.setCurrentIndex(ci if ci!=-1 else 0)
        self.mat_url_edit.setText(str(md.get('ProductPageURL',''))); self.mat_lead_spin.setValue(get_int_val(md.get('LeadTimeDays',0))); self.mat_safe_stock_spin.setValue(get_int_val(md.get('SafetyStockQuantity',0))); self.mat_notes_edit.setText(str(md.get('Notes','')))
    def clear_material_form(self): # ...
        for w in [self.mat_id_edit, self.mat_name_edit, self.mat_cat_edit, self.mat_uom_edit, self.mat_url_edit, self.mat_notes_edit]: w.clear()
        for w in [self.mat_stock_spin, self.mat_rop_spin, self.mat_soq_spin, self.mat_lead_spin, self.mat_safe_stock_spin]: w.setValue(0)
        self.mat_price_spin.setValue(0.0); self.mat_pref_sup_combo.setCurrentIndex(0); self.materials_table_view.clearSelection()
    def refresh_suppliers_table(self): # ...
        if self.suppliers_df is None: print("Suppliers dataframe not available for refreshing table."); return
        self.suppliers_table_view.setRowCount(0); self.suppliers_table_view.setColumnCount(len(SUPPLIERS_HEADERS)); self.suppliers_table_view.setHorizontalHeaderLabels(SUPPLIERS_HEADERS)
        for r, rd in self.suppliers_df.iterrows():
            self.suppliers_table_view.insertRow(r)
            for c, h in enumerate(SUPPLIERS_HEADERS): self.suppliers_table_view.setItem(r, c, QTableWidgetItem(str(rd.get(h, ''))))
        self.suppliers_table_view.resizeColumnsToContents(); self.suppliers_table_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); self.suppliers_table_view.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.suppliers_table_view.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    def on_supplier_selected(self): # ...
        si = self.suppliers_table_view.selectedItems(); sr = self.suppliers_table_view.currentRow()
        if not si or sr < 0 or sr >= len(self.suppliers_df): self.clear_supplier_form(); return
        sd = self.suppliers_df.iloc[sr]; self.sup_id_edit.setText(str(sd.get('SupplierID',''))); self.sup_name_edit.setText(str(sd.get('SupplierName',''))); self.sup_contact_edit.setText(str(sd.get('ContactPerson',''))); self.sup_email_edit.setText(str(sd.get('Email','')))
        self.sup_phone_edit.setText(str(sd.get('Phone',''))); self.sup_website_edit.setText(str(sd.get('Website','')))
        ci = self.sup_order_method_combo.findText(str(sd.get('OrderMethod',''))); self.sup_order_method_combo.setCurrentIndex(ci if ci!=-1 else 0)
    def clear_supplier_form(self): # ...
        for w in [self.sup_id_edit, self.sup_name_edit, self.sup_contact_edit, self.sup_email_edit, self.sup_phone_edit, self.sup_website_edit]: w.clear()
        self.sup_order_method_combo.setCurrentIndex(0); self.suppliers_table_view.clearSelection()
    def save_material_data(self): print(f"Save Material: {self.mat_id_edit.text()}"); # ...
    def save_supplier_data(self): print(f"Save Supplier: {self.sup_id_edit.text()}"); # ...

class ProcurementAppGUI(QMainWindow):
    def __init__(self):
        print("Initializing ProcurementAppGUI...")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Python path: {sys.path}")
        
        try:
            print("\n1. Creating QMainWindow...")
            super().__init__()
            print("  - QMainWindow initialized")
            
            print("\n2. Setting window properties...")
            self.setWindowTitle("Integrated Procurement Application")
            self.setGeometry(50, 50, 1200, 850)
            print("  - Window properties set")

            print("\n3. Creating debug console...")
            self.debug_console = DebugConsole()
            print("  - Debug console created")
            
            print("\n4. Loading materials data...")
            try:
                self.materials_df = load_or_create_dataframe_app(MATERIALS_FILE, MATERIALS_HEADERS, parent_widget=self, create_if_missing=True)
                print(f"  - Successfully loaded {len(self.materials_df)} materials from {MATERIALS_FILE}")
            except Exception as e:
                print(f"  - ERROR loading materials: {str(e)}")
                raise
            
            print("\n5. Loading suppliers data...")
            try:
                self.suppliers_df = load_or_create_dataframe_app(SUPPLIERS_FILE, SUPPLIERS_HEADERS, parent_widget=self, create_if_missing=True)
                print(f"  - Successfully loaded {len(self.suppliers_df)} suppliers from {SUPPLIERS_FILE}")
            except Exception as e:
                print(f"  - ERROR loading suppliers: {str(e)}")
                raise
            
            print("\n6. Setting up UI...")
            try:
                self.setup_ui()
                print("  - UI setup completed successfully")
            except Exception as e:
                print(f"  - ERROR in setup_ui: {str(e)}")
                raise
            
            print("\n=== Application Initialized Successfully ===")
            print(f"Python: {sys.version}")
            try:
                from PyQt6.QtCore import PYQT_VERSION_STR
                print(f"PyQt6 version: {PYQT_VERSION_STR}")
            except Exception as e:
                print(f"Could not get PyQt6 version: {e}")
            print("Ready for use!\n")
            
            # Force the debug console to be visible
            self.debug_console.show()
            
        except Exception as e:
            error_msg = f"FATAL ERROR during initialization: {str(e)}"
            print(f"\n{error_msg}")
            import traceback
            traceback.print_exc()
            
            # Try to show error in a message box if possible
            try:
                QMessageBox.critical(None, "Fatal Error", error_msg)
            except:
                print("Could not display error dialog")
            
            # Re-raise to ensure the application exits
            raise
            
    def setup_data_management_tab(self):
        """Set up the Data Management tab"""
        print("      - Initializing Data Management tab...")
        
        # Create the main layout
        layout = QVBoxLayout()
        
        # Create tab widget for materials and suppliers
        tabs = QTabWidget()
        
        # Materials tab
        materials_tab = QWidget()
        materials_layout = QVBoxLayout()
        
        # Materials table
        self.materials_table = QTableWidget()
        self.materials_table.setColumnCount(8)
        self.materials_table.setHorizontalHeaderLabels([
            "Material ID", "Name", "Description", "Category", 
            "Current Stock", "Reorder Point", "Unit", "Preferred Supplier"
        ])
        self.materials_table.horizontalHeader().setStretchLastSection(True)
        
        # Add materials to table
        self.populate_materials_table()
        
        # Buttons for materials
        materials_btn_layout = QHBoxLayout()
        add_material_btn = QPushButton("Add Material")
        add_material_btn.clicked.connect(self.add_material)
        edit_material_btn = QPushButton("Edit Material")
        edit_material_btn.clicked.connect(self.edit_material)
        delete_material_btn = QPushButton("Delete Material")
        delete_material_btn.clicked.connect(self.delete_material)
        
        materials_btn_layout.addWidget(add_material_btn)
        materials_btn_layout.addWidget(edit_material_btn)
        materials_btn_layout.addWidget(delete_material_btn)
        materials_btn_layout.addStretch()
        
        materials_layout.addWidget(QLabel("<b>Materials</b>"))
        materials_layout.addWidget(self.materials_table)
        materials_layout.addLayout(materials_btn_layout)
        materials_tab.setLayout(materials_layout)
        
        # Suppliers tab
        suppliers_tab = QWidget()
        suppliers_layout = QVBoxLayout()
        
        # Suppliers table
        self.suppliers_table = QTableWidget()
        self.suppliers_table.setColumnCount(6)
        self.suppliers_table.setHorizontalHeaderLabels([
            "Supplier ID", "Name", "Contact", "Email", "Phone", "Website"
        ])
        self.suppliers_table.horizontalHeader().setStretchLastSection(True)
        
        # Add suppliers to table
        self.populate_suppliers_table()
        
        # Buttons for suppliers
        suppliers_btn_layout = QHBoxLayout()
        add_supplier_btn = QPushButton("Add Supplier")
        add_supplier_btn.clicked.connect(self.add_supplier)
        edit_supplier_btn = QPushButton("Edit Supplier")
        edit_supplier_btn.clicked.connect(self.edit_supplier)
        delete_supplier_btn = QPushButton("Delete Supplier")
        delete_supplier_btn.clicked.connect(self.delete_supplier)
        
        suppliers_btn_layout.addWidget(add_supplier_btn)
        suppliers_btn_layout.addWidget(edit_supplier_btn)
        suppliers_btn_layout.addWidget(delete_supplier_btn)
        suppliers_btn_layout.addStretch()
        
        suppliers_layout.addWidget(QLabel("<b>Suppliers</b>"))
        suppliers_layout.addWidget(self.suppliers_table)
        suppliers_layout.addLayout(suppliers_btn_layout)
        suppliers_tab.setLayout(suppliers_layout)
        
        # Add tabs to tab widget
        tabs.addTab(materials_tab, "Materials")
        tabs.addTab(suppliers_tab, "Suppliers")
        
        # Add tab widget to main layout
        layout.addWidget(tabs)
        
        # Add status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
        print("      - Data Management tab initialized successfully")
        return layout
        
    def populate_materials_table(self):
        """Populate the materials table with data"""
        try:
            self.materials_table.setRowCount(0)
            if hasattr(self, 'materials_df') and not self.materials_df.empty:
                for _, row in self.materials_df.iterrows():
                    row_pos = self.materials_table.rowCount()
                    self.materials_table.insertRow(row_pos)
                    
                    self.materials_table.setItem(row_pos, 0, QTableWidgetItem(str(row.get('MaterialID', ''))))
                    self.materials_table.setItem(row_pos, 1, QTableWidgetItem(str(row.get('MaterialName', ''))))
                    self.materials_table.setItem(row_pos, 2, QTableWidgetItem(str(row.get('Description', ''))))
                    self.materials_table.setItem(row_pos, 3, QTableWidgetItem(str(row.get('Category', ''))))
                    self.materials_table.setItem(row_pos, 4, QTableWidgetItem(str(row.get('CurrentStock', ''))))
                    self.materials_table.setItem(row_pos, 5, QTableWidgetItem(str(row.get('ReorderPoint', ''))))
                    self.materials_table.setItem(row_pos, 6, QTableWidgetItem(str(row.get('Unit', ''))))
                    self.materials_table.setItem(row_pos, 7, QTableWidgetItem(str(row.get('PreferredSupplier', ''))))
            
            self.materials_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error populating materials table: {str(e)}")
    
    def populate_suppliers_table(self):
        """Populate the suppliers table with data"""
        try:
            self.suppliers_table.setRowCount(0)
            if hasattr(self, 'suppliers_df') and not self.suppliers_df.empty:
                for _, row in self.suppliers_df.iterrows():
                    row_pos = self.suppliers_table.rowCount()
                    self.suppliers_table.insertRow(row_pos)
                    
                    self.suppliers_table.setItem(row_pos, 0, QTableWidgetItem(str(row.get('SupplierID', ''))))
                    self.suppliers_table.setItem(row_pos, 1, QTableWidgetItem(str(row.get('SupplierName', ''))))
                    self.suppliers_table.setItem(row_pos, 2, QTableWidgetItem(str(row.get('ContactPerson', ''))))
                    self.suppliers_table.setItem(row_pos, 3, QTableWidgetItem(str(row.get('Email', ''))))
                    self.suppliers_table.setItem(row_pos, 4, QTableWidgetItem(str(row.get('Phone', ''))))
                    self.suppliers_table.setItem(row_pos, 5, QTableWidgetItem(str(row.get('Website', ''))))
            
            self.suppliers_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error populating suppliers table: {str(e)}")
    
    def add_material(self):
        """Add a new material"""
        # Implementation for adding a new material
        pass
    
    def edit_material(self):
        """Edit selected material"""
        # Implementation for editing a material
        pass
    
    def delete_material(self):
        """Delete selected material"""
        # Implementation for deleting a material
        pass
    
    def add_supplier(self):
        """Add a new supplier"""
        # Implementation for adding a new supplier
        pass
    
    def edit_supplier(self):
        """Edit selected supplier"""
        # Implementation for editing a supplier
        pass
    
    def delete_supplier(self):
        """Delete selected supplier"""
        # Implementation for deleting a supplier
        pass
    
    def setup_ui(self):
        """Set up the main UI components"""
        print("  - Setting up main UI...")
        
        try:
            # Create the main widget and layout
            main_widget = QWidget()
            main_layout = QVBoxLayout(main_widget)
            
            # Create a splitter for main content and debug console
            splitter = QSplitter(Qt.Orientation.Vertical)
            
            # Create container for the main content
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            
            # Create tab widget for the main content
            self.main_tabs = QTabWidget()
            content_layout.addWidget(self.main_tabs)
            
            # Set up each tab with error handling
            try:
                print("    - Setting up Data Management tab...")
                self.data_management_tab = QWidget()
                self.data_management_tab.setLayout(self.setup_data_management_tab())
                self.main_tabs.addTab(self.data_management_tab, "Data Management")
                print("      - Data Management tab created successfully")
            except Exception as e:
                print(f"      - Error creating Data Management tab: {str(e)}")
                import traceback
                print(traceback.format_exc())
                raise
            
            try:
                print("    - Setting up Order Processing tab...")
                self.order_processing_tab = QWidget()
                order_processing_layout = self.setup_order_processing_tab()
                if order_processing_layout is not None:
                    self.order_processing_tab.setLayout(order_processing_layout)
                    self.main_tabs.addTab(self.order_processing_tab, "Order Processing")
                    print("      - Order Processing tab created successfully")
                else:
                    print("      - Warning: setup_order_processing_tab() returned None")
            except Exception as e:
                print(f"      - Error creating Order Processing tab: {str(e)}")
                import traceback
                print(traceback.format_exc())
                raise
            
            try:
                print("    - Setting up Check-In tab...")
                self.check_in_tab = self.setup_check_in_tab()
                if self.check_in_tab is not None:
                    self.main_tabs.addTab(self.check_in_tab, "Check-In")
                    print("      - Check-In tab created successfully")
                else:
                    print("      - Warning: setup_check_in_tab() returned None")
            except Exception as e:
                print(f"      - Error creating Check-In tab: {str(e)}")
                import traceback
                print(traceback.format_exc())
                raise
            
            # Add content widget and debug console to splitter
            splitter.addWidget(content_widget)
            splitter.addWidget(self.debug_console)
            
            # Set initial sizes (70% for content, 30% for debug console)
            splitter.setSizes([int(self.height() * 0.7), int(self.height() * 0.3)])
            
            # Add splitter to main layout
            main_layout.addWidget(splitter)
            
            # Set the main widget
            self.setCentralWidget(main_widget)
            
            # Set up status bar
            self.statusBar = QStatusBar()
            self.setStatusBar(self.statusBar)
            self.statusBar.showMessage("Ready")
            
            print("  - UI setup completed successfully")
            
        except Exception as e:
            error_msg = f"Error setting up UI: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "UI Setup Error", error_msg)
            raise
            
    def setup_order_processing_tab(self):
        """Set up the Order Processing tab"""
        print("    - Setting up Order Processing tab...")
        
        try:
            # Create a main layout for the tab
            layout = QVBoxLayout()
            
            # Add a title
            title = QLabel("Order Processing")
            title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
            layout.addWidget(title)
            
            # Add a button to generate suggested POs
            self.generate_po_btn = QPushButton("Generate Suggested Purchase Orders")
            self.generate_po_btn.clicked.connect(self.trigger_po_generation)
            layout.addWidget(self.generate_po_btn)
            
            # Add a table to display suggested POs
            self.suggested_po_table = QTableWidget()
            self.suggested_po_table.setColumnCount(6)
            self.suggested_po_table.setHorizontalHeaderLabels([
                "Material ID", "Material Name", "Current Stock", 
                "Reorder Point", "Quantity to Order", "Supplier"
            ])
            self.suggested_po_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.suggested_po_table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            layout.addWidget(QLabel("Suggested Purchase Orders:"))
            layout.addWidget(self.suggested_po_table)
            
            # Add a button to process selected POs
            self.process_po_btn = QPushButton("Process Selected Orders")
            self.process_po_btn.setEnabled(False)
            self.process_po_btn.clicked.connect(self.handle_update_selected_orders)
            layout.addWidget(self.process_po_btn)
            
            # Add a table to display active orders
            self.active_orders_table = QTableWidget()
            self.active_orders_table.setColumnCount(7)
            self.active_orders_table.setHorizontalHeaderLabels([
                "Select", "Order ID", "Material", "Ordered Qty", 
                "Supplier", "Date Ordered", "Status"
            ])
            self.active_orders_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.active_orders_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.active_orders_table.horizontalHeader().setStretchLastSection(True)
            self.active_orders_table.itemSelectionChanged.connect(self.update_active_orders_button_state)
            layout.addWidget(QLabel("Active Orders:"))
            layout.addWidget(self.active_orders_table)
            
            # Add a log area
            self.order_processing_log_area = QTextEdit()
            self.order_processing_log_area.setReadOnly(True)
            self.order_processing_log_area.setMaximumHeight(100)
            layout.addWidget(QLabel("Log:"))
            layout.addWidget(self.order_processing_log_area)
            
            # Load active orders
            self.load_and_display_active_orders()
            
            print("      - Order Processing tab created successfully")
            return layout
            
        except Exception as e:
            print(f"      - Error in setup_order_processing_tab: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Return a basic layout with error message if setup fails
            error_layout = QVBoxLayout()
            error_label = QLabel(f"Error initializing Order Processing tab: {str(e)}")
            error_label.setStyleSheet("color: red;")
            error_layout.addWidget(error_label)
            return error_layout
        
        # Add active orders label and table
        layout.addWidget(QLabel("<b>Active Orders</b>"))
        layout.addWidget(self.active_orders_table)
        
        # Add log area
        self.order_processing_log_area = QTextEdit()
        self.order_processing_log_area.setReadOnly(True)
        self.order_processing_log_area.setMaximumHeight(100)
        layout.addWidget(QLabel("<b>Log</b>"))
        layout.addWidget(self.order_processing_log_area)
        
        return layout
        
    def setup_check_in_tab(self):
        """Set up the Check-In tab for receiving orders"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Order Check-In")
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Add horizontal layout for buttons
        button_layout = QHBoxLayout()
        
        # Refresh button
        self.refresh_check_in_btn = QPushButton("Refresh Orders")
        self.refresh_check_in_btn.clicked.connect(self.load_check_in_orders)
        button_layout.addWidget(self.refresh_check_in_btn)
        
        # Update Selected button
        self.update_check_in_btn = QPushButton("Update Selected")
        self.update_check_in_btn.setEnabled(False)
        self.update_check_in_btn.clicked.connect(self.process_check_in_updates)
        button_layout.addWidget(self.update_check_in_btn)
        
        # Add stretch to push buttons to the left
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Create table for check-in orders
        self.check_in_table = QTableWidget()
        self.check_in_table.setColumnCount(8)
        self.check_in_table.setHorizontalHeaderLabels([
            "Select", "Order ID", "Material", "Ordered Qty", "Supplier", 
            "Date Ordered", "Status", "Check-In Status"
        ])
        self.check_in_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.check_in_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.check_in_table.horizontalHeader().setStretchLastSection(True)
        
        # Add quantity input for partial receipts
        self.quantity_received_label = QLabel("Quantity Received (for partial receipts):")
        self.quantity_received_input = QSpinBox()
        self.quantity_received_input.setMinimum(1)
        self.quantity_received_input.setMaximum(99999)
        
        # Status selection
        self.status_label = QLabel("Update Status:")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Select status...", "Fully Received", "Partially Received", "Wrong Delivery"])
        self.status_combo.currentIndexChanged.connect(self.on_status_changed)
        
        # Notes field
        self.notes_label = QLabel("Notes:")
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        
        # Add input fields to a form layout
        form_layout = QFormLayout()
        form_layout.addRow(self.quantity_received_label, self.quantity_received_input)
        form_layout.addRow(self.status_label, self.status_combo)
        form_layout.addRow(self.notes_label, self.notes_input)
        
        # Add widgets to main layout
        layout.addWidget(self.check_in_table)
        layout.addLayout(form_layout)
        
        # Log area
        self.check_in_log = QTextEdit()
        self.check_in_log.setReadOnly(True)
        self.check_in_log.setMaximumHeight(100)
        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.check_in_log)
        
        tab.setLayout(layout)
        
        # Load initial data
        self.load_check_in_orders()
        
        return tab
        
    def on_status_changed(self, index):
        """Enable/disable quantity input based on status selection"""
        status = self.status_combo.currentText()
        self.quantity_received_input.setEnabled(status == "Partially Received")
        self.quantity_received_label.setEnabled(status == "Partially Received")
    
    def load_check_in_orders(self):
        """Load orders that need to be checked in"""
        try:
            self.check_in_table.setRowCount(0)
            
            # Load order history
            orders_df = load_or_create_dataframe_app(
                ORDER_HISTORY_FILE, 
                ORDER_HISTORY_HEADERS, 
                parent_widget=self
            )
            
            if orders_df.empty:
                self.log_check_in("No orders found.")
                return
                
            # Filter for orders that are not yet fully received or archived
            active_orders = orders_df[
                ~orders_df['Status'].isin(['Fully Received', 'Archived', 'Cancelled'])
            ]
            
            if active_orders.empty:
                self.log_check_in("No orders pending check-in.")
                return
                
            # Populate the table
            for _, order in active_orders.iterrows():
                row = self.check_in_table.rowCount()
                self.check_in_table.insertRow(row)
                
                # Add checkbox
                chkbox = QCheckBox()
                chkbox.stateChanged.connect(self.update_check_in_button_state)
                self.check_in_table.setCellWidget(row, 0, chkbox)
                
                # Add order details
                self.check_in_table.setItem(row, 1, QTableWidgetItem(str(order.get('OrderID', ''))))
                self.check_in_table.setItem(row, 2, QTableWidgetItem(str(order.get('MaterialName', ''))))
                self.check_in_table.setItem(row, 3, QTableWidgetItem(str(order.get('QuantityOrdered', ''))))
                self.check_in_table.setItem(row, 4, QTableWidgetItem(str(order.get('SupplierName', ''))))
                self.check_in_table.setItem(row, 5, QTableWidgetItem(str(order.get('Timestamp', ''))))
                self.check_in_table.setItem(row, 6, QTableWidgetItem(str(order.get('Status', ''))))
                
                # Add status combo box
                status_combo = QComboBox()
                status_combo.addItems(["", "Fully Received", "Partially Received", "Wrong Delivery"])
                self.check_in_table.setCellWidget(row, 7, status_combo)
            
            self.check_in_table.resizeColumnsToContents()
            self.log_check_in(f"Loaded {len(active_orders)} orders pending check-in.")
            
        except Exception as e:
            self.log_check_in(f"Error loading orders: {str(e)}")
            import traceback
            self.log_check_in(traceback.format_exc())
    
    def update_check_in_button_state(self):
        """Enable/disable update button based on selection"""
        any_checked = False
        for row in range(self.check_in_table.rowCount()):
            if self.check_in_table.cellWidget(row, 0).isChecked():
                any_checked = True
                break
        self.update_check_in_btn.setEnabled(any_checked)
    
    def process_check_in_updates(self):
        """Process the check-in updates for selected orders"""
        try:
            # Get the selected status and notes
            status = self.status_combo.currentText()
            notes = self.notes_input.toPlainText()
            
            if status == "Select status...":
                QMessageBox.warning(self, "Warning", "Please select a status.")
                return
                
            # Process each selected row
            updated_count = 0
            
            for row in range(self.check_in_table.rowCount()):
                chkbox = self.check_in_table.cellWidget(row, 0)
                if not chkbox.isChecked():
                    continue
                    
                try:
                    order_id = self.check_in_table.item(row, 1).text()
                    material_name = self.check_in_table.item(row, 2).text()
                    ordered_qty = int(self.check_in_table.item(row, 3).text())
                    
                    # Get the status from the row's combo box
                    status_combo = self.check_in_table.cellWidget(row, 7)
                    row_status = status_combo.currentText()
                    
                    if not row_status:
                        self.log_check_in(f"Order {order_id}: No status selected. Skipping.")
                        continue
                        
                    # Load current order history
                    orders_df = load_or_create_dataframe_app(
                        ORDER_HISTORY_FILE, 
                        ORDER_HISTORY_HEADERS, 
                        parent_widget=self
                    )
                    
                    # Find and update the order
                    order_idx = orders_df.index[orders_df['OrderID'] == order_id].tolist()
                    if not order_idx:
                        self.log_check_in(f"Order {order_id} not found in history.")
                        continue
                        
                    order_idx = order_idx[0]
                    
                    # Update order status
                    if row_status == "Fully Received":
                        received_qty = ordered_qty
                        new_status = "Fully Received"
                    elif row_status == "Partially Received":
                        received_qty = self.quantity_received_input.value()
                        new_status = "Partially Received"
                    else:  # Wrong Delivery
                        received_qty = 0
                        new_status = "Wrong Delivery"
                    
                    # Update the order in history
                    orders_df.at[order_idx, 'Status'] = new_status
                    orders_df.at[order_idx, 'DateReceived'] = datetime.now().strftime("%Y-%m-%d")
                    orders_df.at[order_idx, 'QuantityReceived'] = str(received_qty)
                    orders_df.at[order_idx, 'Notes'] = notes
                    
                    # Save the updated history
                    orders_df.to_csv(ORDER_HISTORY_FILE, index=False)
                    
                    # If fully received, update stock levels
                    if row_status == "Fully Received":
                        self.update_stock_levels(
                            material_name, 
                            received_qty
                        )
                    
                    updated_count += 1
                    self.log_check_in(f"Updated order {order_id} - {material_name}: {new_status}")
                    
                except Exception as e:
                    self.log_check_in(f"Error processing order: {str(e)}")
                    import traceback
                    self.log_check_in(traceback.format_exc())
            
            # Show summary and refresh
            QMessageBox.information(
                self, 
                "Update Complete", 
                f"Successfully updated {updated_count} orders."
            )
            
            # Clear inputs and refresh the table
            self.quantity_received_input.setValue(1)
            self.status_combo.setCurrentIndex(0)
            self.notes_input.clear()
            self.load_check_in_orders()
            
        except Exception as e:
            self.log_check_in(f"Error processing updates: {str(e)}")
            import traceback
            self.log_check_in(traceback.format_exc())
    
    def update_stock_levels(self, material_name, received_qty):
        """Update stock levels when items are received"""
        try:
            # Load materials
            materials_df = load_or_create_dataframe_app(
                MATERIALS_FILE,
                MATERIALS_HEADERS,
                parent_widget=self
            )
            
            # Find the material
            mask = materials_df['MaterialName'].str.lower() == material_name.lower()
            if not mask.any():
                self.log_check_in(f"Material {material_name} not found in inventory.")
                return
                
            # Update stock level
            current_stock = int(materials_df.loc[mask, 'CurrentStock'].iloc[0])
            new_stock = current_stock + received_qty
            materials_df.loc[mask, 'CurrentStock'] = str(new_stock)
            
            # Save updated materials
            materials_df.to_csv(MATERIALS_FILE, index=False)
            self.log_check_in(f"Updated stock for {material_name}: {current_stock} -> {new_stock}")
            
        except Exception as e:
            self.log_check_in(f"Error updating stock levels: {str(e)}")
    
    def log_check_in(self, message):
        """Add a message to the check-in log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.check_in_log.append(f"[{timestamp}] {message}")
        QApplication.processEvents()

    def setup_order_processing_tab(self):
        """Set up the Order Processing tab"""
        print("      - Initializing Order Processing tab...")
        
        try:
            # Create the main layout for the order processing tab
            order_proc_layout = QVBoxLayout()

            # Add title
            title = QLabel("Order Processing")
            title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
            order_proc_layout.addWidget(title)

            # Add Generate POs button
            self.generate_po_btn = QPushButton("Generate New Suggested POs")
            order_proc_layout.addWidget(self.generate_po_btn)

            # Add label for suggested orders
            order_proc_layout.addWidget(QLabel("Suggested Purchase Orders:"))

            # Add table for suggested orders
            self.suggested_po_table = QTableWidget()
            self.suggested_po_table.setColumnCount(8)  # Increased to 8 columns to include all data
            self.suggested_po_table.setHorizontalHeaderLabels([
                "Select", "Material ID", "Material Name", "Current Stock",
                "Reorder Point", "Quantity to Order", "Unit Price", "Supplier"
            ])
            self.suggested_po_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.suggested_po_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)  # We're using checkboxes for selection
            self.suggested_po_table.horizontalHeader().setStretchLastSection(True)
            order_proc_layout.addWidget(self.suggested_po_table)

            # Add Process Selected Orders button
            self.process_po_btn = QPushButton("Process Selected Orders")
            self.process_po_btn.setEnabled(False)
            order_proc_layout.addWidget(self.process_po_btn)

            # Add label for active orders
            order_proc_layout.addWidget(QLabel("Active Orders:"))
            
            # Add table for active orders
            self.active_orders_table = QTableWidget()
            self.active_orders_table.setColumnCount(7)
            self.active_orders_table.setHorizontalHeaderLabels([
                "Select", "Order ID", "Material", "Ordered Qty",
                "Supplier", "Date Ordered", "Status"
            ])
            self.active_orders_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.active_orders_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            self.active_orders_table.horizontalHeader().setStretchLastSection(True)
            order_proc_layout.addWidget(self.active_orders_table)

            # Add log area
            self.order_processing_log_area = QTextEdit()
            self.order_processing_log_area.setReadOnly(True)
            self.order_processing_log_area.setMaximumHeight(100)
            order_proc_layout.addWidget(QLabel("Log:"))
            order_proc_layout.addWidget(self.order_processing_log_area)
            
            # Connect signals
            self.generate_po_btn.clicked.connect(self.trigger_po_generation)
            self.process_po_btn.clicked.connect(self.handle_update_selected_orders)
            self.active_orders_table.itemSelectionChanged.connect(self.update_active_orders_button_state)
            
            # Initial load of active orders
            self.load_and_display_active_orders()
            
            print("      - Order Processing tab initialized")
            return order_proc_layout
            
        except Exception as e:
            print(f"      - Error in setup_order_processing_tab: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Return a basic layout with error message if setup fails
            error_layout = QVBoxLayout()
            error_label = QLabel(f"Error initializing Order Processing tab: {str(e)}")
            error_label.setStyleSheet("color: red;")
            error_layout.addWidget(error_label)
            return error_layout

    def log_to_order_processing_area(self, message):
        if hasattr(self, 'order_processing_log_area') and self.order_processing_log_area:
            self.order_processing_log_area.append(str(message))
            QApplication.processEvents()
        else:
            print(f"OrderProcessingLog: {message}")

    def trigger_po_generation(self):
        self.log_to_order_processing_area("Starting New Suggested PO Generation...")
        try:
            # Import the main function from main.py
            from main import main as generate_suggested_orders
            
            # Clear previous suggestions
            self.suggested_po_table.setRowCount(0)
            
            # Get suggested orders
            suggested_orders = generate_suggested_orders(logger_func=self.log_to_order_processing_area)
            
            # Debug: Print the raw suggested_orders
            print("\n=== DEBUG: Raw suggested_orders ===")
            print(f"Type: {type(suggested_orders)}")
            if isinstance(suggested_orders, list):
                print(f"Length: {len(suggested_orders)}")
                if len(suggested_orders) > 0:
                    print("First item type:", type(suggested_orders[0]))
                    if hasattr(suggested_orders[0], 'keys'):
                        print("First item keys:", suggested_orders[0].keys())
                        # Print the first few items for debugging
                        for i, order in enumerate(suggested_orders[:3]):
                            print(f"\nOrder {i+1} details:")
                            for key, value in order.items():
                                print(f"  {key}: {value}")
                    else:
                        print("First item is not a dictionary:", suggested_orders[0])
            print("==============================\n")
            
            if not suggested_orders or not isinstance(suggested_orders, list):
                self.log_to_order_processing_area("No suggested orders were generated.")
                QMessageBox.information(self, "No Orders", "No suggested purchase orders were generated.")
                return
            
            # Store the current suggestions for processing
            self.current_suggested_orders = suggested_orders
            
            # Load suppliers to map supplier IDs to names
            suppliers_df = load_or_create_dataframe_app(SUPPLIERS_FILE, SUPPLIERS_HEADERS, parent_widget=self)
            supplier_map = {}
            if not suppliers_df.empty and 'SupplierID' in suppliers_df.columns and 'SupplierName' in suppliers_df.columns:
                supplier_map = dict(zip(suppliers_df['SupplierID'], suppliers_df['SupplierName']))
            
            # Populate the table with the suggested orders
            self.suggested_po_table.setRowCount(len(suggested_orders))
            
            for row, order in enumerate(suggested_orders):
                try:
                    # Add checkbox in first column
                    chk = QTableWidgetItem()
                    chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    chk.setCheckState(Qt.CheckState.Unchecked)
                    self.suggested_po_table.setItem(row, 0, chk)
                    
                    # Get supplier name from ID if available
                    supplier_id = str(order.get('PreferredSupplierID', order.get('supplier_id', '')))
                    supplier_name = supplier_map.get(supplier_id, supplier_id)  # Fall back to ID if name not found
                    
                    # Add order details to the table
                    # Use .get() with multiple possible keys to handle different naming conventions
                    self.suggested_po_table.setItem(row, 1, QTableWidgetItem(str(order.get('MaterialID', order.get('material_id', '')))))
                    self.suggested_po_table.setItem(row, 2, QTableWidgetItem(str(order.get('MaterialName', order.get('material_name', 'Unknown')))))
                    self.suggested_po_table.setItem(row, 3, QTableWidgetItem(str(order.get('CurrentStock', order.get('current_stock', '0')))))
                    self.suggested_po_table.setItem(row, 4, QTableWidgetItem(str(order.get('ReorderPoint', order.get('reorder_point', '0')))))
                    
                    # Handle quantity to order
                    quantity = str(order.get('QuantityToOrder', order.get('quantity_to_order', '0')))
                    if quantity == '0':  # Fallback to standard order quantity if quantity is 0
                        quantity = str(order.get('StandardOrderQuantity', '0'))
                    self.suggested_po_table.setItem(row, 5, QTableWidgetItem(quantity))
                    
                    # Handle unit price
                    unit_price = str(order.get('UnitPrice', order.get('unit_price', '0.00')))
                    if unit_price == '0.00':  # Fallback to current price if unit price is 0
                        unit_price = str(order.get('CurrentPrice', '0.00'))
                    self.suggested_po_table.setItem(row, 6, QTableWidgetItem(unit_price))
                    
                    # Add supplier name
                    self.suggested_po_table.setItem(row, 7, QTableWidgetItem(supplier_name))
                    
                except Exception as e:
                    print(f"Error processing order row {row}: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    continue
            
            # Resize columns to fit content
            self.suggested_po_table.resizeColumnsToContents()
            
            # Enable the Process Selected Orders button if we have orders
            if len(suggested_orders) > 0:
                self.process_po_btn.setEnabled(True)
                self.log_to_order_processing_area(f"{len(suggested_orders)} suggested purchase orders are ready for review.")
            else:
                self.process_po_btn.setEnabled(False)
                self.log_to_order_processing_area("No suggested purchase orders were generated.")
            
        except Exception as e:
            error_msg = f"An error occurred during PO generation: {str(e)}"
            self.log_to_order_processing_area(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
            import traceback
            self.log_to_order_processing_area(traceback.format_exc())
            print(f"Error in trigger_po_generation: {str(e)}")
            print(traceback.format_exc())

    def update_active_orders_button_state(self):
        any_checked = False
        if hasattr(self, 'active_orders_table'):
            for i in range(self.active_orders_table.rowCount()):
                # Checkbox is a cell widget
                cell_widget = self.active_orders_table.cellWidget(i, 0) # Assuming 'Select' is column 0
                if isinstance(cell_widget, QCheckBox) and cell_widget.isChecked():
                    any_checked = True
                    break
        if hasattr(self, 'update_selected_orders_btn'):
            self.update_selected_orders_btn.setEnabled(any_checked)

    def handle_update_selected_orders(self):
        self.log_to_order_processing_area("Processing selected purchase orders...")
        
        try:
            # Get checked rows from the suggested PO table
            selected_rows = []
            for row in range(self.suggested_po_table.rowCount()):
                item = self.suggested_po_table.item(row, 0)  # Checkbox is in column 0
                if item and item.checkState() == Qt.CheckState.Checked:
                    selected_rows.append(row)
            
            if not selected_rows:
                QMessageBox.warning(self, "No Selection", "Please check one or more orders to process.")
                return
                
            # Get the suggested orders data
            if not hasattr(self, 'current_suggested_orders') or not self.current_suggested_orders:
                self.log_to_order_processing_area("Error: No suggested orders data found.")
                return
                
            # Load existing order history or create empty DataFrame if it doesn't exist
            try:
                order_history = pd.read_csv(ORDER_HISTORY_FILE, dtype=str)
                order_history = order_history.where(pd.notnull(order_history), None)
            except (FileNotFoundError, pd.errors.EmptyDataError):
                order_history = pd.DataFrame(columns=ORDER_HISTORY_HEADERS)
            
            # Process each selected order
            processed_orders = []
            for row in selected_rows:
                if row >= len(self.current_suggested_orders):
                    continue
                    
                order = self.current_suggested_orders[row]
                
                # Create a new order record
                new_order = {
                    'OrderID': generate_order_id(),
                    'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'MaterialID': str(order.get('material_id', '')),
                    'MaterialName': str(order.get('material_name', '')),
                    'QuantityOrdered': str(order.get('quantity_to_order', '')),
                    'UnitPricePaid': str(order.get('unit_price', '0.00')),
                    'TotalPricePaid': str(float(order.get('quantity_to_order', 0)) * float(order.get('unit_price', 0))),
                    'SupplierID': str(order.get('supplier_id', '')),
                    'SupplierName': str(order.get('supplier_name', '')),
                    'OrderMethod': 'Manual',
                    'Status': 'Ordered',
                    'QuantityReceived': '0',
                    'DateReceived': '',
                    'Notes': 'Generated from suggested orders'
                }
                
                # Add to order history
                order_history = pd.concat([order_history, pd.DataFrame([new_order])], ignore_index=True)
                processed_orders.append(order.get('material_name', 'Unknown'))
                
                self.log_to_order_processing_area(f"Created order for {order.get('material_name', '')} (Qty: {order.get('quantity_to_order', '')})")
            
            if not processed_orders:
                self.log_to_order_processing_area("No valid orders to process.")
                return
                
            # Save the updated order history
            try:
                self.save_any_dataframe(order_history, ORDER_HISTORY_FILE, ORDER_HISTORY_HEADERS)
                self.log_to_order_processing_area(f"Successfully saved {len(processed_orders)} order(s) to history.")
                
                # Remove processed orders from current suggestions
                # Process in reverse order to maintain correct indices
                for row in sorted(selected_rows, reverse=True):
                    if row < len(self.current_suggested_orders):
                        self.current_suggested_orders.pop(row)
                        self.suggested_po_table.removeRow(row)
                
                # Disable the process button if no more suggestions
                if self.suggested_po_table.rowCount() == 0:
                    self.process_po_btn.setEnabled(False)
                
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"Successfully processed {len(processed_orders)} order(s).\n"
                    f"Materials: {', '.join(processed_orders)}"
                )
                
                # Refresh the active orders display
                self.load_and_display_active_orders()
                
            except Exception as save_error:
                error_msg = f"Error saving order history: {str(save_error)}"
                self.log_to_order_processing_area(error_msg)
                QMessageBox.critical(self, "Save Error", error_msg)
                raise
            
        except Exception as e:
            error_msg = f"Error processing orders: {str(e)}"
            self.log_to_order_processing_area(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
            import traceback
            self.log_to_order_processing_area(traceback.format_exc())
            
            # Refresh the display
            self.load_and_display_active_orders()

    def load_and_display_active_orders(self):
        """Load and display active orders in the order processing tab"""
        try:
            if not hasattr(self, 'order_processing_log_area'):
                print("Error: order_processing_log_area not initialized.")
                return
                
            self.order_processing_log_area.clear()
            self.order_processing_log_area.append("Loading active orders...")
            QApplication.processEvents()
            
            # Load order history
            current_order_history_df = load_or_create_dataframe_app(
                ORDER_HISTORY_FILE, 
                ORDER_HISTORY_HEADERS, 
                parent_widget=self
            )
            
            if current_order_history_df.empty:
                self.order_processing_log_area.append("No order history found.")
                return
                
            # Clean and normalize status column
            if 'Status' in current_order_history_df.columns:
                current_order_history_df['Status'] = current_order_history_df['Status'].astype(str).str.strip()
                # Normalize status values
                status_mapping = {
                    'ordered': 'Ordered',
                    'partially received': 'Partially Received',
                    'partially_received': 'Partially Received',
                    'received': 'Fully Received',
                    'cancelled': 'Cancelled',
                    'issue': 'Issue Reported',
                    'issue reported': 'Issue Reported'
                }
                current_order_history_df['Status'] = current_order_history_df['Status'].str.lower().map(status_mapping).fillna(current_order_history_df['Status'])
            
            # Filter for active orders (Ordered or Partially Received)
            active_orders = current_order_history_df[
                current_order_history_df['Status'].isin(['Ordered', 'Partially Received'])
            ].copy()
            
            # Configure the table
            columns = [
                'Select', 'OrderID', 'MaterialName', 'Quantity Ordered', 
                'Supplier', 'Status', 'Date Ordered', 'Check-In Status'
            ]
            
            self.active_orders_table.setRowCount(0)
            self.active_orders_table.setColumnCount(len(columns))
            self.active_orders_table.setHorizontalHeaderLabels(columns)
            
            # Populate the table with active orders
            for row_idx, order in active_orders.iterrows():
                self.active_orders_table.insertRow(row_idx)
                
                # Add checkbox for selection
                chkbox = QCheckBox()
                chkbox.setChecked(False)
                chkbox.stateChanged.connect(self.update_active_orders_button_state)
                self.active_orders_table.setCellWidget(row_idx, 0, chkbox)
                
                # Add order details
                self.active_orders_table.setItem(row_idx, 1, QTableWidgetItem(str(order.get('OrderID', ''))))
                self.active_orders_table.setItem(row_idx, 2, QTableWidgetItem(str(order.get('MaterialName', ''))))
                self.active_orders_table.setItem(row_idx, 3, QTableWidgetItem(str(order.get('QuantityOrdered', ''))))
                self.active_orders_table.setItem(row_idx, 4, QTableWidgetItem(str(order.get('SupplierName', ''))))
                self.active_orders_table.setItem(row_idx, 5, QTableWidgetItem(str(order.get('Status', ''))))
                self.active_orders_table.setItem(row_idx, 6, QTableWidgetItem(str(order.get('Timestamp', ''))))
                
                # Add status dropdown
                status_combo = QComboBox()
                status_combo.addItems(["", "Fully Received", "Partially Received", "Issue Reported", "Cancelled"])
                self.active_orders_table.setCellWidget(row_idx, 7, status_combo)
            
            # Resize columns to fit content
            self.active_orders_table.resizeColumnsToContents()
            self.order_processing_log_area.append(f"Loaded {len(active_orders)} active orders.")
            
            # Update the button state based on selections
            self.update_active_orders_button_state()
            
        except Exception as e:
            error_msg = f"Error loading active orders: {str(e)}"
            self.log_to_order_processing_area(error_msg)
            import traceback
            self.log_to_order_processing_area(traceback.format_exc())
            QMessageBox.critical(self, "Error", error_msg)

    def display_suggested_orders(self, suggested_orders):
        """Display suggested purchase orders in the order processing tab"""
        self.log_to_order_processing_area("Displaying suggested purchase orders...")
        
        # Define columns for the suggested orders table
        columns = [
            'Select', 'MaterialID', 'MaterialName', 'Current Stock', 
            'Reorder Point', 'Quantity to Order', 'Unit Price', 'Supplier', 'Total'
        ]
        
        # Configure the table
        self.active_orders_table.setRowCount(0)
        self.active_orders_table.setColumnCount(len(columns))
        self.active_orders_table.setHorizontalHeaderLabels(columns)
        
        # Populate the table with suggested orders
        for row_idx, order in enumerate(suggested_orders):
            self.active_orders_table.insertRow(row_idx)
            
            # Add checkbox for selection
            chkbox = QCheckBox()
            chkbox.setChecked(True)  # Default to selected
            chkbox.stateChanged.connect(self.update_active_orders_button_state)
            self.active_orders_table.setCellWidget(row_idx, 0, chkbox)
            
            # Add order details
            self.active_orders_table.setItem(row_idx, 1, QTableWidgetItem(str(order.get('MaterialID', ''))))
            self.active_orders_table.setItem(row_idx, 2, QTableWidgetItem(str(order.get('MaterialName', ''))))
            self.active_orders_table.setItem(row_idx, 3, QTableWidgetItem(str(order.get('CurrentStock', ''))))
            self.active_orders_table.setItem(row_idx, 4, QTableWidgetItem(str(order.get('ReorderPoint', ''))))
            self.active_orders_table.setItem(row_idx, 5, QTableWidgetItem(str(order.get('QuantityToOrder', ''))))
            self.active_orders_table.setItem(row_idx, 6, QTableWidgetItem(f"£{float(order.get('UnitPrice', 0)):.2f}"))
            self.active_orders_table.setItem(row_idx, 7, QTableWidgetItem(str(order.get('PreferredSupplierID', ''))))
            
            # Calculate and add total
            quantity = float(order.get('QuantityToOrder', 0))
            unit_price = float(order.get('UnitPrice', 0))
            total = quantity * unit_price
            self.active_orders_table.setItem(row_idx, 8, QTableWidgetItem(f"£{total:.2f}"))
        
        # Resize columns to fit content
        self.active_orders_table.resizeColumnsToContents()
        self.log_to_order_processing_area(f"Displayed {len(suggested_orders)} suggested purchase orders.")

    def save_any_dataframe(self, df, file_path, headers_order=None, create_backup=True):
        # Placeholder implementation - actual logic might be needed later
        print(f"Attempting to save dataframe to {file_path} (placeholder action)")
        try:
            # A more complete placeholder might try to use pandas to_csv
            if headers_order:
                df.to_csv(file_path, index=False, columns=headers_order)
            else:
                df.to_csv(file_path, index=False)
            print(f"Placeholder: Successfully saved {file_path}")
            # QMessageBox.information(self, "Success", f"Data saved to {file_path}")
        except Exception as e:
            print(f"Placeholder: Error saving to {file_path}: {e}")
            # QMessageBox.critical(self, "Save Error", f"Error saving to {file_path}: {e}")

    def refresh_preferred_supplier_dropdown_in_materials_tab(self):
        # Placeholder implementation
        print("Refreshing preferred supplier dropdown (placeholder action)")
        # Actual logic would involve accessing UI elements, which is complex for a placeholder
        pass

def initialize_application_data():
    """Initialize all required data files with proper structure if they don't exist"""
    # Define required files and their default structures
    required_files = {
        MATERIALS_FILE: {
            'columns': MATERIALS_HEADERS,
            'sample_data': [
                ['MAT-001', 'Sample Material', 'General', 'pcs', '100', '20', '50', 'SUP-001', 
                 'https://example.com', '5', '10', 'Sample material', '9.99']
            ]
        },
        SUPPLIERS_FILE: {
            'columns': SUPPLIERS_HEADERS,
            'sample_data': [
                ['SUP-001', 'Sample Supplier', 'John Doe', 'john@example.com', '123-456-7890', 
                 'https://example.com', 'Email']
            ]
        },
        ORDER_HISTORY_FILE: {
            'columns': ORDER_HISTORY_HEADERS,
            'sample_data': []  # Empty for order history
        },
        'procurement_rules.json': {
            'content': '{"rules": []}'
        }
    }

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    
    # Initialize each required file if it doesn't exist
    for file_path, config in required_files.items():
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            try:
                if file_path.endswith('.csv'):
                    df = pd.DataFrame(columns=config['columns'])
                    if config['sample_data']:
                        df = pd.DataFrame(config['sample_data'], columns=config['columns'])
                    df.to_csv(file_path, index=False)
                elif file_path.endswith('.json'):
                    with open(file_path, 'w') as f:
                        f.write(config['content'])
                print(f"Created {file_path} with default structure")
            except Exception as e:
                print(f"Failed to initialize {file_path}: {str(e)}")

if __name__ == '__main__':
    print("Starting application initialization...")
    
    # Initialize QApplication first
    print("1. Creating QApplication instance...")
    try:
        app = QApplication(sys.argv)
        print("  - QApplication created successfully")
    except Exception as e:
        print(f"  - ERROR creating QApplication: {str(e)}")
        sys.exit(1)
    
    # Initialize required data files
    print("\n2. Initializing application data...")
    try:
        initialize_application_data()
        print("  - Application data initialized successfully")
    except Exception as e:
        print(f"  - ERROR during data initialization: {str(e)}")
        error_msg = f"Failed to initialize application data:\n{str(e)}"
        QMessageBox.critical(None, "Initialization Error", error_msg)
        sys.exit(1)
    
    # Create and show the main window
    print("\n3. Creating main application window...")
    try:
        main_app_window = ProcurementAppGUI()
        print("  - Main window created successfully")
        
        # Show the main window
        print("  - Showing main window...")
        main_app_window.show()
        print("  - Main window shown")
        
        # Start the event loop
        print("\nStarting application event loop...")
        sys.exit(app.exec())
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\nFATAL ERROR: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        
        error_msg = f"""
        A fatal error occurred while starting the application:
        {str(e)}
        
        Please check the following:
        1. All required data files exist in the application directory
        2. You have the required permissions to read/write files
        3. All dependencies are installed (run 'pip install -r requirements.txt')
        
        Detailed error information has been printed to the console.
        """
        
        try:
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Application Error")
            error_dialog.setText("Failed to start application")
            error_dialog.setInformativeText(str(e))
            error_dialog.setDetailedText(error_trace)
            error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            error_dialog.exec()
        except Exception as dialog_error:
            print(f"Failed to show error dialog: {str(dialog_error)}")
        
        sys.exit(1)
