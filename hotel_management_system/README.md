# Odoo Hotel Management (hotel_management_system)

## Customization Checklist

Local changes to the upstream Webkul module. Review before upgrading or merging upstream updates.

- [x] **`models/sale_order.py`** — `_onchange_check_in_out` has been **blocked** (`@api.onchange` decorator and method body commented out). Check-in/check-out onchange no longer normalizes dates via `change_hotel_check_in_out` or updates room line `product_uom_qty` from stay duration.

## Overview
Odoo Hotel Management is a comprehensive module designed to streamline hotel operations. From managing rooms and bookings to housekeeping and hotel services, this module provides an all-in-one solution for hotel management, both via the backend and the website.

## Dependencies
- This module is dependent on the `wk_wizard_messages` module.

## Features

### Booking Management
- **Backend Bookings**:
  - Admin or hotel staff can create bookings, assign rooms, and manage room services and housekeeping.
- **Website Bookings**:
  - Customers can book rooms through the website by providing details like name, age, number of members, and contact information.

### Housekeeping Management
- Assign housekeeping tasks to hotel employees automatically or manually after a booking is checked out.
- **Configuration Options**:
  - Set housekeeping assignments to **Auto** or **Manual** in hotel settings (via `Settings`).

### Hotel Services Management
- Define hotel services (e.g., laundry, car parking, 24/7 service, WiFi, etc.) in the backend.
- Assign paid or free services to bookings:
  - Paid services like laundry can be added to the customer's bill/sale order/booking.
  - Services requiring inventory items will adjust stock levels accordingly.
- Assign specific services to hotel employees for execution.

### Dashboards
- **General Dashboard**:
  - Calendar view highlighting all bookings.
  - Overview of available rooms, check-ins, and check-outs.
- **Owner Dashboard**:
  - Widgets for:
    - Total revenue.
    - Today's check-ins.
    - Today's bookings.
    - Revenue comparison with previous periods.
  - Graphs displaying various data points.
  - Period selection options (e.g., Last 7 Days, Last Week, Last 30 Days, Last 6 Months, Years).

## Installation

### Option 1: Using Custom Addons Directory
1. Place the `hotel_management_system` module folder inside your custom-addons directory.
2. Restart your Odoo instance to make the module available.

### Option 2: Using the Odoo UI
1. Log in to your Odoo backend.
2. Navigate to **Apps** and click on the **Import Module** button.
3. Upload the module zip file and install it.

## Configuration

1. **Housekeeping Assignment**:
   - Navigate to **Settings** in the backend.
   - Select **Auto** or **Manual** assignment for housekeeping in the hotel settings.

2. **Hotel Services**:
   - Define hotel services (paid or free) in the backend.
   - Assign services to bookings as needed.

3. **Dashboards**:
   - Access dashboards from the backend to view bookings, revenue, and other insights.


## Benefits
- Streamlines hotel operations, enhancing efficiency and customer satisfaction.
- Offers a robust system for managing bookings, housekeeping, and hotel services.
- Provides insights through interactive dashboards to support better decision-making.


### Credits
- **Author**: Webkul Software Pvt. Ltd.


