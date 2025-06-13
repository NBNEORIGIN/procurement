import sqlite3
from datetime import datetime
from database import db # Assuming db instance provides get_connection()
import logging

logger = logging.getLogger('procurement_order_processing')

def get_stock_levels():
    """Retrieve current and minimum stock levels for all materials."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, current_stock, min_stock FROM materials")
            # Return as a dictionary: {material_id: (name, current_stock, min_stock)}
            # Corrected to return name as well, as it's useful for display and matches select
            return {row[0]: {'name': row[1], 'current_stock': row[2], 'min_stock': row[3]} for row in cursor.fetchall()}
    except sqlite3.Error as e:
        logger.error(f"Failed to get stock levels: {e}")
        return {}

def create_order(material_id, qty):
    """Create a new order and reserve stock.
    Uses an atomic transaction.
    """
    try:
        with db.get_connection() as conn: # Ensures atomicity (commit on success, rollback on error)
            cursor = conn.cursor()
            # 1. Record the order
            cursor.execute(
                "INSERT INTO orders (material_id, order_qty, order_date, is_processed) VALUES (?, ?, datetime('now', 'localtime'), 0)",
                (material_id, qty)
            )
            order_id = cursor.lastrowid

            # 2. Reduce current_stock (reserve stock)
            # This means current_stock reflects "available for new orders/use"
            cursor.execute(
                "UPDATE materials SET current_stock = current_stock - ? WHERE id = ?",
                (qty, material_id)
            )
            logger.info(f"Order {order_id} created for material {material_id}, quantity {qty}. Stock reserved.")
            conn.commit() # Explicit commit, though context manager handles it on successful exit.
            return order_id # Return the new order ID
    except sqlite3.Error as e:
        logger.error(f"Order creation failed for material {material_id}, qty {qty}: {e}")
        # Transaction is automatically rolled back by context manager if an exception occurs
        return None # Indicate failure

def process_order(order_id):
    """Mark an order as processed (e.g., sent to supplier).
    Uses an atomic transaction.
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Check if already processed
            cursor.execute("SELECT is_processed FROM orders WHERE id = ?", (order_id,))
            status_row = cursor.fetchone()

            if status_row is None:
                logger.error(f"Process order failed: Order ID {order_id} not found.")
                return False

            if status_row[0] == 1: # is_processed is already true
                logger.warning(f"Order {order_id} is already processed.")
                return False # No change made

            # Mark as processed
            cursor.execute("UPDATE orders SET is_processed = 1, updated_at = datetime('now', 'localtime') WHERE id = ?", (order_id,))
            logger.info(f"Order {order_id} marked as processed.")
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"Failed to process order {order_id}: {e}")
        return False

def receive_order(order_id, received_qty, status):
    """Record receipt of goods and update stock.
    'status' can be "FULL", "PARTIAL", "WRONG".
    Uses an atomic transaction.
    """
    if status not in ("FULL", "PARTIAL", "WRONG"):
        logger.error(f"Invalid status '{status}' for receive_order.")
        return False

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Check if order exists and get material_id
            cursor.execute("SELECT material_id FROM orders WHERE id = ?", (order_id,))
            order_row = cursor.fetchone()
            if order_row is None:
                logger.error(f"Receive order failed: Order ID {order_id} not found.")
                return False
            material_id = order_row[0]

            # 2. Update receipt log (receipts table)
            cursor.execute(
                "INSERT INTO receipts (order_id, received_qty, status, receipt_date) VALUES (?, ?, ?, datetime('now', 'localtime'))",
                (order_id, received_qty, status)
            )
            receipt_id = cursor.lastrowid

            # 3. Adjust stock if FULL/PARTIAL and received_qty > 0.
            # Stock was already reduced at order creation (reserved).
            # Now, we add the received quantity to make it physically available.
            if status in ("FULL", "PARTIAL") and received_qty > 0:
                cursor.execute(
                    "UPDATE materials SET current_stock = current_stock + ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (received_qty, material_id)
                )

            # If status is "WRONG", stock is not typically adjusted unless it implies a return or loss,
            # which would be a separate inventory adjustment process.
            # If "WRONG" means items were incorrect and returned to supplier,
            # then the "reserved" stock might need to be "un-reserved" or handled via credit note.
            # For now, "WRONG" only logs the receipt and doesn't auto-adjust stock.

            logger.info(f"Receipt {receipt_id} recorded for order {order_id}, material {material_id}, qty {received_qty}, status {status}. Stock updated accordingly.")
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"Failed to receive order {order_id}, qty {received_qty}, status {status}: {e}")
        return False

if __name__ == '__main__':
    # Basic configuration for logging if running this file directly for testing
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()])
    logger.info("Order processing module direct run - for testing.")

    # Example Usage (requires procurement.db to be set up with new schema)
    # Ensure you have the db object initialized from database.py correctly
    # from database import Database
    # db_instance = Database() # To ensure tables are created if not already

    # Test get_stock_levels
    # print("Stock Levels:", get_stock_levels())

    # --- Test Create Order ---
    # Assuming material ID 1 exists and has enough stock to "reserve" 5 units
    # initial_stock = get_stock_levels().get(1, {}).get('current_stock', 0)
    # print(f"Initial stock for material 1: {initial_stock}")
    # new_order_id = create_order(material_id=1, qty=5)
    # if new_order_id:
    #    print(f"Created order ID: {new_order_id}")
    #    updated_stock = get_stock_levels().get(1, {}).get('current_stock', 0)
    #    print(f"Stock for material 1 after order creation: {updated_stock}")
    #    # Expected: initial_stock - 5
    # else:
    #    print("Failed to create order.")

    # --- Test Process Order ---
    # if new_order_id:
    #    print(f"Processing order {new_order_id}...")
    #    if process_order(new_order_id):
    #        print(f"Order {new_order_id} processed.")
    #        # Verify is_processed flag in DB
    #    else:
    #        print(f"Failed to process order {new_order_id}.")

    # --- Test Receive Order ---
    # if new_order_id:
    #    print(f"Receiving order {new_order_id} (full quantity)...")
    #    initial_stock_before_receipt = get_stock_levels().get(1, {}).get('current_stock', 0)
    #    print(f"Stock for material 1 before receipt: {initial_stock_before_receipt}")
    #    if receive_order(order_id=new_order_id, received_qty=5, status="FULL"):
    #        print(f"Order {new_order_id} received in full.")
    #        final_stock = get_stock_levels().get(1, {}).get('current_stock', 0)
    #        print(f"Stock for material 1 after full receipt: {final_stock}")
    #        # Expected: initial_stock_before_receipt + 5 (which should be the original initial_stock)
    #    else:
    #        print(f"Failed to receive order {new_order_id}.")

    # Example: Receive a partial order
    # another_order_id = create_order(material_id=1, qty=10) # Assume material 1 exists
    # if another_order_id:
    #    process_order(another_order_id) # Mark as processed
    #    print(f"Receiving partial for order {another_order_id} (3 of 10)...")
    #    stock_before_partial = get_stock_levels().get(1, {}).get('current_stock', 0)
    #    print(f"Stock for material 1 before partial receipt: {stock_before_partial}")
    #    if receive_order(order_id=another_order_id, received_qty=3, status="PARTIAL"):
    #        print("Partial receipt recorded.")
    #        stock_after_partial = get_stock_levels().get(1, {}).get('current_stock', 0)
    #        print(f"Stock for material 1 after partial receipt: {stock_after_partial}")
    #        # Expected: stock_before_partial + 3
    #    else:
    #        print("Failed to record partial receipt.")

    # Example: Receive a wrong order
    # wrong_order_id = create_order(material_id=1, qty=2) # Assume material 1 exists
    # if wrong_order_id:
    #    process_order(wrong_order_id)
    #    print(f"Receiving 'wrong' for order {wrong_order_id} (received 0 usable)...")
    #    stock_before_wrong = get_stock_levels().get(1, {}).get('current_stock', 0)
    #    print(f"Stock for material 1 before 'wrong' receipt: {stock_before_wrong}")
    #    if receive_order(order_id=wrong_order_id, received_qty=0, status="WRONG"): # Or received_qty could be >0 if wrong items were delivered but not added to stock
    #        print("'Wrong' receipt recorded.")
    #        stock_after_wrong = get_stock_levels().get(1, {}).get('current_stock', 0)
    #        print(f"Stock for material 1 after 'wrong' receipt: {stock_after_wrong}")
    #        # Expected: stock_before_wrong (no change from this receipt)
    #    else:
    #        print("Failed to record 'wrong' receipt.")
    pass
