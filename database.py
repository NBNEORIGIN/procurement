import sqlite3
import os
import logging
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('procurement_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('procurement_db')

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if self.initialized:
            return
            
        self.initialized = True
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'procurement.db')
        self.conn = None
        logger.info(f"Initializing database at {self.db_path}")
        self._setup_database()
    
    def get_connection(self):
        """Create and return a database connection."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn
    
    def _setup_database(self):
        """Create database tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Drop tables if they exist to ensure clean schema update
            logger.debug("Dropping existing tables if they exist")
            cursor.execute("DROP TABLE IF EXISTS checkins;")
            cursor.execute("DROP TABLE IF EXISTS receipts;") # In case of previous partial rename
            cursor.execute("DROP TABLE IF EXISTS orders;")
            cursor.execute("DROP TABLE IF EXISTS materials;")

            # Create tables
            logger.debug("Creating tables with the new schema")

            # Materials Table
            cursor.execute('''
                CREATE TABLE materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    current_stock REAL DEFAULT 0,
                    min_stock REAL DEFAULT 0,
                    reorder_point REAL DEFAULT 0,
                    order_method TEXT,
                    supplier TEXT,
                    order_url TEXT,
                    contact TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logger.debug("Created table: materials")

            # Orders Table
            cursor.execute('''
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_id INTEGER NOT NULL,
                    order_qty REAL NOT NULL,
                    is_processed BOOLEAN DEFAULT 0,
                    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (material_id) REFERENCES materials (id)
                )
            ''')
            logger.debug("Created table: orders")

            # Receipts Table
            cursor.execute('''
                CREATE TABLE receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    received_qty REAL NOT NULL,
                    status TEXT NOT NULL, -- "FULL", "PARTIAL", "WRONG"
                    receipt_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders (id)
                )
            ''')
            logger.debug("Created table: receipts")
            
            # Create triggers for updated_at
            triggers = {
                'update_materials_timestamp': '''
                    CREATE TRIGGER update_materials_timestamp
                    AFTER UPDATE ON materials
                    BEGIN
                        UPDATE materials SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = OLD.id;
                    END;
                ''',
                'update_orders_timestamp': '''
                    CREATE TRIGGER update_orders_timestamp
                    AFTER UPDATE ON orders
                    BEGIN
                        UPDATE orders SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = OLD.id;
                    END;
                '''
                # No trigger for receipts table for now, as updated_at is not a field.
            }
            
            for trigger_name, create_trigger_sql in triggers.items():
                logger.debug(f"Creating trigger: {trigger_name}")
                # Ensure triggers are also created fresh by dropping them if they exist
                cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name};")
                cursor.execute(create_trigger_sql)
            
            conn.commit()
            logger.info("Database setup completed successfully")

# Initialize the database when this module is imported
db = Database()
