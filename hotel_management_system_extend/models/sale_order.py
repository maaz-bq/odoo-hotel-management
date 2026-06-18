# -*- coding: utf-8 -*-

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange("hotel_id", "order_line")
    def _onchange_hotel_id_is_room_type(self):
        has_room_lines = any(
            line.product_id.is_room_type
            for line in self.order_line
            if line.product_id
        )
        self.is_room_type = bool(self.hotel_id or has_room_lines)

    @api.depends_context("lang")
    @api.depends(
        "order_line.price_subtotal",
        "currency_id",
        "company_id",
        "payment_term_id",
        "booking_id.hotel_service_lines.amount",
        "booking_id.hotel_service_lines.service_type",
        "paid_amount",
        "balance_amount",
        "payment_ids.amount",
        "amount_total",
    )
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for order in self:
            tax_totals = order.tax_totals
            if not tax_totals:
                continue

            subtotals = [
                subtotal
                for subtotal in tax_totals.get("subtotals", [])
                if subtotal.get("name") not in ("Paid Amount", "Balance Amount")
            ]
            order.tax_totals = {
                **tax_totals,
                "subtotals": subtotals,
                "paid_amount_currency": order.paid_amount,
                "balance_amount_currency": order.balance_amount,
            }
