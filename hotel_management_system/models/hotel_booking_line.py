# -*- coding: utf-8 -*-
##########################################################################
# Author : Webkul Software Pvt. Ltd. (<https://webkul.com/>;)
# Copyright(c): 2017-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>;
##########################################################################
import datetime as dt
import uuid
import logging
from datetime import datetime, timedelta
import pytz
import base64
from collections import defaultdict

import logging
_logger = logging.getLogger(__name__)

from odoo import fields, models, api, _
from odoo.http import request
from odoo.exceptions import ValidationError, UserError

class HotelBookingLine(models.Model):
    _name = "hotel.booking.line"
    _description = "Booking Line"
    _rec_name = "product_id"

    booking_sequence_id = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _("New"),
    )
    image_1920 = fields.Image(related="product_id.image_1920")
    product_id = fields.Many2one("product.product", string="Rooms")
    booking_id = fields.Many2one("hotel.booking", readonly=True, copy=False)
    guest_info_ids = fields.One2many(
        "guest.info", "booking_line_id", string="Members", required=True
    )
    price = fields.Float(string="Price Per Night", compute="_compute_amount")
    description = fields.Html("Description ", compute="_get_description", store=True)
    tax_ids = fields.Many2many("account.tax", string="Taxes")
    subtotal_price = fields.Float(string="Subtotal", compute="_compute_amount")
    taxed_price = fields.Float(string="taxed amount", compute="_compute_amount")
    currency_id = fields.Many2one(related="booking_id.currency_id", string="Currency")
    status_bar = fields.Selection(related="booking_id.status_bar", copy=False)
    product_tmpl_id = fields.Many2one(
        "product.template", related="product_id.product_tmpl_id"
    )
    max_child = fields.Integer(related="product_tmpl_id.max_child", string="Max Child")
    max_adult = fields.Integer(related="product_tmpl_id.max_adult", string="Max Adult")
    sale_order_line_id = fields.Many2one("sale.order.line", string="Sale Order Line")
    housekeeping_id = fields.Many2one("hotel.housekeeping", string="HouseKeeping")
    check_in = fields.Datetime(related="booking_id.check_in")
    check_out = fields.Datetime(related="booking_id.check_out")
    hotel_service_lines = fields.One2many(
        "hotel.booking.service.line",
        "booking_line_id",
        string="Service Lines",
    )
    warning = fields.Text(string="Warning In Hotel Booking Line", compute="_compute_warning", store=True, readonly=False)

    discount = fields.Float(
        string="Discount (%)",
        readonly=False,
        digits='Discount')

    service_line_id = fields.Many2one('hotel.booking.service.line')
    booking_days = fields.Integer(string="Days Book For", compute="_compute_booking_days", copy=False)
    name = fields.Text(string="Description", readonly=False)
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")
    
    product_type = fields.Selection(related="product_id.type")
    max_occupancy = fields.Integer(related="product_tmpl_id.max_occupancy", string="Max Occupancy")
    base_occupancy = fields.Integer(related="product_tmpl_id.base_occupancy", string="Base Occupancy")
    extra_charge_per_person = fields.Monetary(related="product_tmpl_id.extra_charge_per_person", string="Extra Charge per person")


    @api.depends('guest_info_ids', 'guest_info_ids.is_adult')
    def _compute_warning(self):
        for line in self:
            adult = sum(1 for guest in line.guest_info_ids if guest.is_adult)
            child = len(line.guest_info_ids) - adult
            total_guests = adult + child

            if not line.guest_info_ids:
                line.warning = "Please fill the members details !!"
            elif line.max_adult < adult and line.max_child < child:
                line.warning = "No. of Adult Guests and Child Guests cannot be greater than Max Adult and Child count"
            elif line.max_adult < adult:
                line.warning = "No. of Adult Guests cannot be greater than Max Adult count"
            elif line.max_child < child:
                line.warning = "No. of Child Guests cannot be greater than Max Child count"
            elif total_guests > line.max_occupancy:
                line.warning = "Total number of guests cannot exceed the maximum occupancy limit"
            else:
                line.warning = ""

    @api.onchange("subtotal_price")
    @api.depends(
        "product_id",
        "price",
        "tax_ids",
        "discount",
        "subtotal_price",
        "booking_id.check_out",
        "booking_id.check_in",
    )
    def _compute_amount(self):
        for line in self:
            extra_cost=0
            if line.guest_info_ids:
                total_guests=len(line.guest_info_ids)
                line.price = line.booking_id.pricelist_id._get_product_price(line.product_id, line.booking_days)
                if total_guests > line.base_occupancy:
                    extra_guests=total_guests-line.base_occupancy
                    extra_cost=extra_guests*line.extra_charge_per_person
                    line.price +=extra_cost

            discounted_price = line.price * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids.compute_all(
                discounted_price,
                line.booking_id.currency_id,
                1,
                product=line.product_id,
            )
            line.subtotal_price = taxes["total_excluded"] * line.booking_days
            line.taxed_price = taxes["total_included"] * line.booking_days

    @api.depends("product_id")
    def _get_description(self):
        for line in self:
            if line.product_id.is_room_type and line.product_id.description_sale:
                line.description = line.product_id.description_sale
            elif line.service_line_id:
                line.description = line.service_line_id.booking_line_id.product_id.display_name
            else:
                line.description = ""

    def write(self, vals):
        self.ensure_one()
        rec = super().write(vals)

        if self.env.context.get("bypass_for_exchange_room"):
            return rec
        

        if self.sale_order_line_id:
            self.sale_order_line_id.write({
                                    "tax_id": self.tax_ids,
                                    "product_id": self.product_id.id,
                                    "product_uom_qty" : self.booking_days,
                                    "price_unit" : self.price,
                                    "guest_info_ids": self.guest_info_ids,
                                    "discount": self.discount
                                    })
        return rec

    def sale_order_view(self):
        active_id = self.id
        return {
            "name": "Sale Order",
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "list",
            "domain": [("booking_line_id", "=", active_id)],
            "target": "new",
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "company_id" in vals:
                self = self.with_company(vals["company_id"])
            if vals.get("booking_sequence_id", _("New")) == _("New"):
                vals["booking_sequence_id"] = self.env["ir.sequence"].next_by_code(
                    "hotel.booking.line"
                ) or _("New")
        
        return super().create(vals_list)
    
    @api.onchange("product_id")
    def _onchange_product_id_set_taxes(self):
        for line in self:
            if line.product_id:
                line.tax_ids = line.product_id.taxes_id

            if line.product_id and line.booking_id.pricelist_id:
                line.price = line.booking_id.pricelist_id._get_product_price(
                    line.product_id, line.booking_days
                )

    @api.depends('product_id', 'booking_id.booking_days', 'service_line_id')
    def _compute_booking_days(self):
        for line in self:
            if line.product_id and line.product_id.is_room_type:
                line.booking_days = line.booking_id.booking_days or 0
            elif line.service_line_id:
                line.booking_days = 1
            else:
                line.booking_days = 0
