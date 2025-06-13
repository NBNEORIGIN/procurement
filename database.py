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
            
            # Create tables if they don't exist
            logger.debug("Creating tables if they don't exist")
            tables = {
                'materials': '''
                    CREATE TABLE IF NOT EXISTS materials (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        type TEXT NOT NULL,
                        name TEXT NOT NULL,
                        unit TEXT NOT NULL,
                        current_qty REAL DEFAULT 0,
                        min_qty REAL DEFAULT 0,
                        reorder_point REAL DEFAULT 0,
                        order_method TEXT,
                        supplier TEXT,
                        link TEXT,
                        contact TEXT,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''',
                'orders': '''
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        material_id INTEGER NOT NULL,
                        quantity_ordered REAL NOT NULL,
                        status TEXT DEFAULT 'Pending',
                        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expected_delivery_date TIMESTAMP,
                        notes TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (material_id) REFERENCES materials (id)
                    )
                ''',
                'checkins': '''
                    CREATE TABLE IF NOT EXISTS checkins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL,
                        received_qty REAL NOT NULL,
                        status TEXT NOT NULL,
                        notes TEXT,
                        checkin_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (order_id) REFERENCES orders (id)
                    )
                '''
            }
            
            # Create tables
            for table_name, create_sql in tables.items():
                logger.debug(f"Creating table: {table_name}")
                cursor.execute(create_sql)
            
            # Create triggers for updated_at
            triggers = {
                'update_materials_timestamp': '''
                    CREATE TRIGGER IF NOT EXISTS update_materials_timestamp
                    AFTER UPDATE ON materials
                    BEGIN
                        UPDATE materials SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = OLD.id;
                    END;
                ''',
                'update_orders_timestamp': '''
                    CREATE TRIGGER IF NOT EXISTS update_orders_timestamp
                    AFTER UPDATE ON orders
                    BEGIN
                        UPDATE orders SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = OLD.id;
                    END;
                '''
            }
            
            for trigger_name, create_trigger in triggers.items():
                logger.debug(f"Creating trigger: {trigger_name}")
                cursor.execute(create_trigger)
            
            conn.commit()
            logger.info("Database setup completed successfully")

# Initialize the database when this module is imported
db = Database()
