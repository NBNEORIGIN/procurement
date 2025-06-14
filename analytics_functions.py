import sqlite3
from datetime import datetime # Not strictly needed if JULIANDAY is used, but good for other date ops
from database import db
import logging

logger = logging.getLogger('procurement.analytics_functions')

def calculate_average_lead_time_per_material():
    """
    Calculates the average lead time in days for each material.
    Lead time is defined as the time from order_date to the receipt_date of the first receipt
    associated with that order. Considers all orders that have at least one receipt where the
    receipt date is on or after the order date.
    Returns a dictionary: {material_id: average_lead_time_days}
    """
    lead_times_by_material = {} # Stores {material_id: [lead_time1_for_order, lead_time2_for_order, ...]}

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # SQL query to calculate lead time in days for each order that has valid receipts.
            # JULIANDAY provides the number of days since noon in Greenwich on November 24, 4714 B.C.
            # The difference between two JULIANDAY values is the number of days.
            # MIN(r.receipt_date) ensures we consider the first receipt for a given order.
            sql = """
            SELECT
                o.material_id,
                JULIANDAY(MIN(r.receipt_date)) - JULIANDAY(o.order_date) as lead_time_days
            FROM orders o
            JOIN receipts r ON o.id = r.order_id
            WHERE
                o.order_date IS NOT NULL
                AND r.receipt_date IS NOT NULL
                AND JULIANDAY(r.receipt_date) >= JULIANDAY(o.order_date) -- Basic sanity check
            GROUP BY o.id -- Group by order_id to get the lead time for each order based on its first receipt
            ORDER BY o.material_id;
            """
            # Note: The result of this query is one row per order that meets the criteria,
            # containing (material_id_for_that_order, lead_time_for_that_order).
            # We then aggregate these per material_id in Python.

            cursor.execute(sql)
            per_order_lead_times = cursor.fetchall()

            for material_id, lead_time_days_for_order in per_order_lead_times:
                if lead_time_days_for_order is None: # Should be filtered by WHERE, but good to check
                    logger.warning(f"Skipping order with NULL lead_time_days for material_id {material_id}")
                    continue

                if material_id not in lead_times_by_material:
                    lead_times_by_material[material_id] = []
                lead_times_by_material[material_id].append(float(lead_time_days_for_order))

            avg_lead_times = {}
            for material_id, times_list in lead_times_by_material.items():
                if times_list: # Ensure there are lead times to average
                    avg_lead_times[material_id] = sum(times_list) / len(times_list)

            if not avg_lead_times and per_order_lead_times: # Data existed but aggregation failed somehow
                 logger.warning("Lead times were found for orders, but final aggregation per material is empty.")
            elif not per_order_lead_times:
                 logger.info("No orders with valid receipts found to calculate lead times.")

            logger.info(f"Calculated average lead times for materials: {avg_lead_times}")
            return avg_lead_times

    except sqlite3.Error as e:
        logger.error(f"Database error while calculating average lead times: {e}", exc_info=True)
        return {}
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"Unexpected error calculating average lead times: {e}", exc_info=True)
        return {}

def calculate_average_order_quantity_per_material():
    """
    Calculates the average order quantity for each material.
    Returns a dictionary: {material_id: average_order_quantity}
    """
    avg_quantities = {}
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            sql = """
            SELECT
                material_id,
                AVG(order_qty) as average_quantity
            FROM orders
            GROUP BY material_id;
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            for material_id, avg_qty in results:
                if avg_qty is not None:
                    avg_quantities[material_id] = float(avg_qty)

            logger.info(f"Calculated average order quantities: {avg_quantities}")
            return avg_quantities
    except sqlite3.Error as e:
        logger.error(f"Database error calculating average order quantities: {e}", exc_info=True)
        return {}
    except Exception as e:
        logger.error(f"Unexpected error calculating average order quantities: {e}", exc_info=True)
        return {}

def count_recent_orders_per_material(days=90):
    """
    Counts the number of orders placed for each material in the last 'days' days.
    Returns a dictionary: {material_id: count_of_recent_orders}
    """
    recent_order_counts = {}
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # Calculate the date 'days' ago from today
            # Using date('now', '-X days') for SQLite
            sql = f"""
            SELECT
                material_id,
                COUNT(id) as order_count
            FROM orders
            WHERE order_date >= DATE('now', '-{int(days)} days')
            GROUP BY material_id;
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            for material_id, count in results:
                recent_order_counts[material_id] = int(count)

            logger.info(f"Calculated recent order counts (last {days} days): {recent_order_counts}")
            return recent_order_counts
    except sqlite3.Error as e:
        logger.error(f"Database error counting recent orders: {e}", exc_info=True)
        return {}
    except Exception as e:
        logger.error(f"Unexpected error counting recent orders: {e}", exc_info=True)
        return {}

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()]) # Ensure handler is present

    logger.info("Testing analytics functions...")

    # Test calculate_average_lead_time_per_material
    avg_times = calculate_average_lead_time_per_material()
    if avg_times:
        for mat_id, time_val in avg_times.items():
            logger.info(f"Material ID: {mat_id}, Avg Lead Time: {time_val:.2f} days")
    else:
        logger.info("No average lead times calculated or an error occurred.")

    # Test calculate_average_order_quantity_per_material
    avg_qtys = calculate_average_order_quantity_per_material()
    if avg_qtys:
        for mat_id, qty_val in avg_qtys.items():
            logger.info(f"Material ID: {mat_id}, Avg Order Qty: {qty_val:.2f}")
    else:
        logger.info("No average order quantities calculated or an error occurred.")

    # Test count_recent_orders_per_material
    recent_orders = count_recent_orders_per_material(days=90)
    if recent_orders:
        for mat_id, count_val in recent_orders.items():
            logger.info(f"Material ID: {mat_id}, Orders in last 90 days: {count_val}")
    else:
        logger.info("No recent order counts calculated or an error occurred.")
