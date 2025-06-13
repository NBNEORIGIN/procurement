# NBNE Procurement System

A desktop application for managing procurement processes, inventory, and supplier relationships built with Python and PyQt6.

## Features

- **Material Management**: Track all materials with detailed attributes
- **Supplier Management**: Manage supplier information and contacts
- **Order Processing**: Generate and track purchase orders
- **Check-In System**: Log received items and update inventory

## Installation

1. Clone the repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

To start the application, run:
```
python main.py
```

## Project Structure

- `main.py`: Application entry point and main window
- `database.py`: Database connection and table definitions
- `requirements.txt`: Python dependencies

## Development Status

### Phase 1: Setup & Core Structure (✔️ Complete)
- [x] Project initialization
- [x] Database schema setup
- [x] Basic main window with tabbed interface

### Phase 2: Material Entry Module (In Progress)
- [ ] Material entry form
- [ ] Data validation
- [ ] Save functionality

### Phase 3: Reorder Processing Module (Pending)
- [ ] Low-stock materials list
- [ ] Order creation
- [ ] Status tracking

### Phase 4: Check-In Module (Pending)
- [ ] Pending orders list
- [ ] Check-in form
- [ ] Inventory updates

## License

MIT
