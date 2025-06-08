import json # Not strictly needed for this version, but good for future if loading supplier details here

# --- Configuration ---
YOUR_COMPANY_NAME = "NBNE"
YOUR_COMPANY_CONTACT_INFO = "Toby Fletcher"\
Regards,

The Procurement Team
Your Company Name
[Your Phone Number]
[Your Email Address]
[Your Website (Optional)]
"""

def generate_po_email(supplier_name, supplier_email, items_to_order):
    """
    Generates a formatted draft email string for a purchase order.

    Args:
        supplier_name (str): The name of the supplier.
        supplier_email (str): The email address of the supplier.
        items_to_order (list): A list of dictionaries, where each dictionary
                               should have 'name' (str) and 'quantity' (any) keys.
                               Example: [{'name': 'Raw Material A', 'quantity': 100},
                                         {'name': 'Component B', 'quantity': 50}]

    Returns:
        str: A formatted email string.
    """

    if not supplier_name or not supplier_email:
        return "Error: Supplier name or email missing."
    if not items_to_order:
        return f"Error: No items provided for order to {supplier_name}."

    subject = f"Purchase Order - {YOUR_COMPANY_NAME} - Order for {supplier_name}"

    greeting = f"Dear {supplier_name} team,"

    item_list_string = ""
    for item in items_to_order:
        item_name = item.get('name', 'N/A')
        item_quantity = item.get('quantity', 'N/A')
        item_list_string += f"- {item_name}: {item_quantity}\n"

    if not item_list_string: # Should not happen if items_to_order is validated, but as a safeguard
        item_list_string = "No specific items detailed in this order request. Please clarify."

    body = f"""\
{greeting}

Please find below our purchase order:

{item_list_string}

Could you please confirm receipt of this order and provide an estimated delivery date?

If you have any questions, please don't hesitate to contact us.

{YOUR_COMPANY_CONTACT_INFO}
"""

    # Constructing the full email string (often useful for logging or before sending)
    # For now, we'll just return the body, but you could return subject and body separately
    # or a fully formed email string if using smtplib later.
    
    # Full email draft (can be printed or logged)
    full_email_draft = f"To: {supplier_email}\n"
    full_email_draft += f"Subject: {subject}\n"
    full_email_draft += "---\n" # Separator
    full_email_draft += body

    return full_email_draft # Or just body, depending on how main.py will use it.
                           # Returning the full draft is good for the "print to console" step.

# --- Example Usage (for testing this script directly) ---
if __name__ == "__main__":
    print("Testing generate_po_email function...")

    # Example supplier data (normally this would come from suppliers.json in main.py)
    example_supplier_name = "Test Supplier Inc."
    example_supplier_email = "test@supplier.com"

    # Example items to order
    example_items = [
        {'name': 'Blue Widgets', 'quantity': 100},
        {'name': 'Red Gadgets', 'quantity': 50, 'unit_price': 10.99}, # Extra info ignored by current func
        {'name': 'Green Gizmos', 'quantity': 75}
    ]
    
    draft_email_output = generate_po_email(example_supplier_name, example_supplier_email, example_items)
    
    print("\n--- Example Draft Email Output ---")
    print(draft_email_output)

    print("\n--- Testing with missing items ---")
    draft_email_no_items = generate_po_email(example_supplier_name, example_supplier_email, [])
    print(draft_email_no_items)
    
    print("\n--- Testing with missing supplier details ---")
    draft_email_no_supplier = generate_po_email("", "", example_items)
    print(draft_email_no_supplier)
