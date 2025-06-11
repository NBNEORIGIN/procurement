# Procurement Management System

A desktop application for managing procurement processes, inventory, and supplier relationships.

## Features

### Data Management Hub
- **Materials Management**: Track all materials with details like:
  - Material ID and Name
  - Category (e.g., Ink, Paper)
  - Unit of Measure
  - Current Stock Levels
  - Reorder Points
  - Standard Order Quantities
  - Product Page URLs
  - Lead Times
  - Safety Stock Quantities
  - Notes
  - Current Prices

- **Suppliers Management**:
  - Supplier ID and Name
  - Contact Information (Person, Email, Phone)
  - Website
  - Preferred Order Method (Online, Email, Phone)

### Order Processing
- Automatically generates purchase orders based on stock levels
- Tracks order history and status
- Provides a centralized view of all active orders

## Getting Started

### Prerequisites
- Python 3.8+
- Required packages (install using `pip install -r requirements.txt`):
  - PyQt6
  - pandas
  - numpy

### Installation
1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python procurement_app_gui.py
   ```
   or on Windows:
   ```
   run_procurement_app.bat
   ```

## Usage

1. **Initial Setup**:
   - Add your materials in the Data Management Hub
   - Add supplier information
   - Set reorder points and standard order quantities for each material

2. **Generating Orders**:
   - Navigate to the Order Processing tab
   - Click "Generate New Suggested POs" to create purchase orders for items below reorder levels
   - Review and update quantities as needed
   - Click "Update Selected Orders" to confirm

3. **Managing Orders**:
   - Track order status in the Order Processing tab
   - View order history for reference
   - Update received quantities as shipments arrive

## File Structure

- `procurement_app_gui.py`: Main application window and UI
- `main.py`: Core order processing logic
- `logic.py`: Business logic functions
- `action.py`: Email and notification handling
- `data/`: Directory containing data files
  - `materials_master.csv`: Material information
  - `suppliers.csv`: Supplier information
  - `order_history.csv`: Record of all orders
  - `procurement_rules.json`: Business rules for ordering

## Troubleshooting

- If the application fails to start, check the following:
  - All required Python packages are installed
  - Data files exist in the correct location
  - You have read/write permissions for the application directory

## License

This project is licensed under the MIT License.
