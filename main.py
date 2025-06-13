import sys
import os
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                            QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSlot

from database import db
from material_entry import MaterialEntryWidget
from materials_list import MaterialsListWidget
from reorder_list import ReorderListWidget
from checkin_widget import CheckInWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NBNE Procurement System")
        self.setMinimumSize(1024, 768)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Setup tabs
        self.setup_material_tab()
        self.setup_reorder_tab()
        self.setup_checkin_tab()
        
        # Add tabs to the tab widget
        self.tabs.addTab(self.material_tab, "Material Management")
        self.tabs.addTab(self.reorder_tab, "Reorder List")
        self.tabs.addTab(self.checkin_tab, "Check-In")

        # Export button
        self.export_button = QPushButton("Export All Data to CSV")
        self.export_button.clicked.connect(self.export_to_csv)

        export_layout = QHBoxLayout()
        export_layout.addStretch()
        export_layout.addWidget(self.export_button)
        export_layout.addStretch()

        layout.addLayout(export_layout)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def setup_material_tab(self):
        """Set up the Material Management tab with list and entry views."""
        # Create a container widget for the material management tab
        self.material_tab = QWidget()
        layout = QVBoxLayout(self.material_tab)
        
        # Button to switch between list and entry views
        self.toggle_view_btn = QPushButton("Add New Material")
        self.toggle_view_btn.clicked.connect(self.toggle_material_view)
        
        # Create stack for list and entry views
        self.material_stack = QWidget()
        self.stack_layout = QVBoxLayout(self.material_stack)
        
        # Create and add widgets to stack
        self.materials_list = MaterialsListWidget()
        self.material_entry = MaterialEntryWidget()
        
        # Connect signals
        self.materials_list.edit_requested.connect(self.edit_material)
        self.material_entry.material_saved.connect(self.on_material_saved)
        
        # Add to layout
        self.stack_layout.addWidget(self.materials_list)
        self.stack_layout.addWidget(self.material_entry)
        self.material_entry.hide()  # Start with list view
        
        # Add widgets to main layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.toggle_view_btn)
        
        layout.addLayout(button_layout)
        layout.addWidget(self.material_stack)
        
        # Track current view
        self.showing_entry_form = False
    
    @pyqtSlot()
    def toggle_material_view(self):
        """Toggle between list and entry views."""
        self.showing_entry_form = not self.showing_entry_form
        
        if self.showing_entry_form:
            self.materials_list.hide()
            self.material_entry.show()
            self.toggle_view_btn.setText("View Materials List")
            self.tabs.setTabText(0, "Add/Edit Material")
        else:
            self.materials_list.show()
            self.material_entry.hide()
            self.toggle_view_btn.setText("Add New Material")
            self.tabs.setTabText(0, "Material Management")
    
    @pyqtSlot(dict)
    def edit_material(self, material_data):
        """Switch to edit mode with the given material data."""
        if not self.showing_entry_form:
            self.toggle_material_view()
        self.material_entry.populate_form(material_data)
    
    @pyqtSlot()
    def on_material_saved(self):
        """Handle material saved signal."""
        self.materials_list.load_materials()
        if hasattr(self, 'reorder_widget'):
            self.reorder_widget.load_reorder_items()
        if self.showing_entry_form:
            self.toggle_material_view()
            
    def on_orders_created(self):
        """Handle orders created signal."""
        # Refresh any widgets that might be affected by new orders
        if hasattr(self, 'materials_list'):
            self.materials_list.load_materials()
    
    def setup_reorder_tab(self):
        """Set up the reorder list tab."""
        self.reorder_tab = QWidget()
        layout = QVBoxLayout(self.reorder_tab)
        
        # Create and add the reorder list widget
        self.reorder_widget = ReorderListWidget()
        self.reorder_widget.orders_created.connect(self.on_orders_created)
        
        layout.addWidget(self.reorder_widget)
    
    def setup_checkin_tab(self):
        """Set up the check-in tab."""
        self.checkin_tab = QWidget()
        layout = QVBoxLayout(self.checkin_tab)
        
        # Create and add the check-in widget
        self.checkin_widget = CheckInWidget()
        self.checkin_widget.data_changed.connect(self.on_checkins_processed)
        
        layout.addWidget(self.checkin_widget)
    
    def on_checkins_processed(self):
        """Handle check-ins processed signal."""
        # Refresh the materials and reorder list to show updated quantities
        self.materials_list.load_materials()
        self.reorder_widget.load_reorder_items()

    @pyqtSlot()
    def export_to_csv(self):
        # import pandas as pd # Already imported at top level
        # import os # Already imported at top level
        # from PyQt6.QtWidgets import QMessageBox # Already imported at top level
        # from database import db # db object is available globally

        try:
            conn = db.get_connection()

            materials_df = pd.read_sql_query("SELECT * FROM materials", conn)
            orders_df = pd.read_sql_query("SELECT * FROM orders", conn)
            receipts_df = pd.read_sql_query("SELECT * FROM receipts", conn)

            # It's good practice to close the connection if it's not managed by a context manager elsewhere
            # However, db.get_connection() in this app returns a connection that might be reused.
            # For read-only operations like this, if the connection is a class member and managed,
            # explicit closing here might be premature. But if it's a fresh one, it should be closed.
            # Assuming db.get_connection() provides a fresh connection or manages its lifecycle appropriately
            # and it's safe to close after use if it was intended for this single operation.
            # Let's assume for now that closing it is fine. If issues arise, this could be revisited.
            if conn:
                conn.close()

            output_dir = os.path.dirname(db.db_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir) # Ensure directory exists, though for db.db_path's dir it should.

            materials_path = os.path.join(output_dir, "materials_export.csv")
            orders_path = os.path.join(output_dir, "orders_export.csv")
            receipts_path = os.path.join(output_dir, "receipts_export.csv")

            materials_df.to_csv(materials_path, index=False)
            orders_df.to_csv(orders_path, index=False)
            receipts_df.to_csv(receipts_path, index=False)

            QMessageBox.information(self, "Export Successful",
                                    f"Data exported to:\n{materials_path}\n{orders_path}\n{receipts_path}")

        except Exception as e:
            # import logging # Assuming logger is part of the class or module
            # logger.error(f"CSV Export failed: {e}", exc_info=True) # For now, direct critical message
            QMessageBox.critical(self, "Export Failed", f"Failed to export data to CSV: {str(e)}")


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
