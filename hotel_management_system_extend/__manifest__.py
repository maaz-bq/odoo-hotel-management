# -*- coding: utf-8 -*-
{
    "name": "Hotel Management System Extend",
    "summary": "Extends hotel sale orders with portal/report fields and always-visible payment totals.",
    "version": "18.0.1.0.0",
    "category": "Generic Modules/Hotel Reservation",
    "depends": [
        "hotel_management_system",
    ],
    "data": [
        "report/sale_order_report_templates.xml",
        "report/tax_totals_templates.xml",
        "views/sale_portal_templates.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
