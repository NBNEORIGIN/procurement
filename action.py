import smtplib
import os # For environment variables
from email.mime.text import MIMEText

# --- Email Configuration (MUST BE COMPLETED AND HANDLED SECURELY) ---
SMTP_SERVER = os.environ.get('PROCUREMENT_SMTP_SERVER', 'smtp.ionos.co.uk') # Example: 'smtp.gmail.com'
SMTP_PORT = int(os.environ.get('PROCUREMENT_SMTP_PORT', 465)) # Example: 587 for TLS, 465 for SSL
SMTP_SENDER_EMAIL = os.environ.get('PROCUREMENT_SMTP_SENDER_EMAIL', 'orders@nbnesigns.com')
# IMPORTANT: Use environment variables or a secure method for the password
SMTP_SENDER_PASSWORD = os.environ.get('PROCUREMENT_SMTP_PASSWORD', '!49Monkswood')
SMTP_USE_TLS = os.environ.get('PROCUREMENT_SMTP_USE_TLS', 'True').lower() == 'true' # Use TLS by default

# --- Company Configuration (from previous version) ---
YOUR_COMPANY_NAME = "NBNE" # Customize this
YOUR_COMPANY_CONTACT_INFO = """Regards,

The Procurement Team
Your Company Name
[Your Phone Number]
[Your Email Address]
[Your Website (Optional)]"""


def generate_po_email_content(supplier_name, items_to_order):
    """
    Generates the subject and body for a purchase order email.

    Args:
        supplier_name (str): The name of the supplier.
        items_to_order (list): A list of dictionaries, each with 'name' and 'quantity'.

    Returns:
        tuple: (subject, body_text) or (None, None) if error.
    """
    if not supplier_name:
        print("Error generating email content: Supplier name missing.")
        return None, None
    if not items_to_order:
        print(f"Error generating email content: No items provided for order to {supplier_name}.")
        return None, None

    subject = f"Purchase Order - {YOUR_COMPANY_NAME} - Order for {supplier_name}"
    greeting = f"Dear {supplier_name} team,"

    item_list_string = ""
    for item in items_to_order:
        item_name = item.get('name', 'N/A')
        item_quantity = item.get('quantity', 'N/A')
        item_list_string += f"- {item_name}: {item_quantity}\n"

    body = f"""\
{greeting}

Please find below our purchase order:

{item_list_string}

Could you please confirm receipt of this order and provide an estimated delivery date?

If you have any questions, please don\'t hesitate to contact us.

{YOUR_COMPANY_CONTACT_INFO}
"""
    return subject, body

def send_po_email(recipient_email, subject, body_text):
    """
    Sends an email using SMTP.

    Args:
        recipient_email (str): The email address of the recipient.
        subject (str): The subject of the email.
        body_text (str): The plain text body of the email.

    Returns:
        bool: True if email was sent successfully, False otherwise.
    """
    if not all([recipient_email, subject, body_text]):
        print("Error sending email: Missing recipient, subject, or body.")
        return False
    
    if not SMTP_SENDER_EMAIL or SMTP_SENDER_EMAIL == 'your_email@example.com' or \
       not SMTP_SENDER_PASSWORD or SMTP_SENDER_PASSWORD == 'YOUR_APP_PASSWORD_OR_REGULAR_PASSWORD' or \
       not SMTP_SERVER or SMTP_SERVER == 'your_smtp_server.com':
        print("Error: SMTP server, sender email, or password not configured.")
        print("Please set PROCUREMENT_SMTP_SERVER, PROCUREMENT_SMTP_PORT, PROCUREMENT_SMTP_SENDER_EMAIL, and PROCUREMENT_SMTP_PASSWORD environment variables.")
        return False

    msg = MIMEText(body_text)
    msg['Subject'] = subject
    msg['From'] = SMTP_SENDER_EMAIL
    msg['To'] = recipient_email

    try:
        print(f"Attempting to send email to {recipient_email} via {SMTP_SERVER}:{SMTP_PORT}...")
        if SMTP_PORT == 465: # Explicitly handle port 465 for SSL
            print("Using SMTP_SSL for port 465.")
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10) # Added timeout
        elif SMTP_USE_TLS: # Handle STARTTLS for other ports like 587
            print("Using SMTP with STARTTLS.")
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) # Added timeout
            server.starttls()
        else: # Fallback for other non-TLS, non-465 scenarios
            print("Using basic SMTP (no explicit TLS/SSL).")
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) # Added timeout
        
        print(f"Attempting login with {SMTP_SENDER_EMAIL}...")
        server.login(SMTP_SENDER_EMAIL, SMTP_SENDER_PASSWORD)
        server.sendmail(SMTP_SENDER_EMAIL, recipient_email, msg.as_string())
        server.quit()
        print(f"Email successfully sent to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: Could not login. Check email/password. Details: {e}")
    except smtplib.SMTPServerDisconnected as e:
        print(f"SMTP Server Disconnected: Check server address and port. Details: {e}")
    except smtplib.SMTPConnectError as e:
        print(f"SMTP Connect Error: Could not connect to server. Details: {e}")
    except TimeoutError as e: # Catch explicit timeout
        print(f"SMTP Timeout Error: Connection attempt timed out. Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while sending email: {e}")
    return False

# --- Example Usage (for testing this script directly) ---
if __name__ == "__main__":
    print("Testing email functions...")

    example_supplier_name = "Test Supplier Inc."
    example_recipient_email = "test_recipient@example.com" # Change to a real email you can check for testing
    example_items = [
        {'name': 'Blue Widgets', 'quantity': 100},
        {'name': 'Red Gadgets', 'quantity': 50}
    ]

    # 1. Generate email content
    subject, body = generate_po_email_content(example_supplier_name, example_items)

    if subject and body:
        print(f"\n--- Email Content Generated ---")
        print(f"Recipient: {example_recipient_email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        
        # 2. Send the email
        # IMPORTANT: For this test to work, you MUST configure SMTP settings above
        # or via environment variables.
        # Use a test recipient email you have access to.
        
        # print("\n--- Attempting to Send Email (ensure SMTP settings are correct) ---")
        # success = send_po_email(example_recipient_email, subject, body)
        # if success:
        #     print("Test email sent successfully (check the recipient's inbox).")
        # else:
        #     print("Test email failed to send. Check SMTP configurations and error messages above.")
        print("\n--- To test sending, uncomment the send_po_email call above ---")
        print("--- AND ensure your SMTP settings and credentials are correctly set via environment variables or temporarily in the script (NOT recommended for production). ---")

    else:
        print("Failed to generate email content for testing.")
