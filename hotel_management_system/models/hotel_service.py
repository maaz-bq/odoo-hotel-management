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

# Odoo Module
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class HotelService(models.Model):
    _name = "hotel.service"
    _description = "Hotel Services"

    def _default_product_id(self):
        service_product = self.env.ref("hotel_management_system.product_hotel_service")
        return service_product.id if service_product else False

    name = fields.Char("Name")
    logo = fields.Binary("Logo")
    color = fields.Integer()
    amount_type = fields.Selection(
        [("fixed", "Fixed")], string="Amount Type", default="fixed", required=True
    )
    service_type = fields.Selection(
        [("free", "Free"), ("paid", "Paid")],
        string="Service Type",
        default="free",
        required=True,
    )
    product_id = fields.Many2one(
        "product.product",
        default=_default_product_id,
        string="Service Product",
    )
    amount = fields.Float("Amount", related="product_id.lst_price", readonly=False)

    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)", "Service will unique always!!!"),
    ]

class HotelBookingServiceLine(models.Model):
    _name = "hotel.booking.service.line"
    _description = "Service Line in Booking"
    _rec_name = "sequence_id"

    sequence_id = fields.Char(
        string="Sequence",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _("New"),
    )
    booking_line_id = fields.Many2one(
        "hotel.booking.line",
        string="Booking Line",
        required=True,
        domain="[('booking_id', '=', booking_id), ('product_id.is_room_type', '=', True)]",
    )
    booking_id = fields.Many2one(
        "hotel.booking",
        string="Booking",
        related="booking_line_id.booking_id",
        store=True,
        readonly=True,
    )
    service_id = fields.Many2one("hotel.service", string="Service", required=True)
    amount = fields.Float("Amount")
    assign_to = fields.Many2one("res.partner", string="Assign To")
    image_1920 = fields.Image("Image", related="service_id.logo", readonly=True)
    product_id = fields.Many2one(related="service_id.product_id", readonly=False)
    amount_type = fields.Selection(
        related="service_id.amount_type",
        readonly=True,
        string="Amount Type",
    )
    note = fields.Text("Notes")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirm"),
            ("done", "Done"),
            ("cancel", "Cancel"),
        ],
        default="draft",
        string="state",
    )
    service_type = fields.Selection(related="service_id.service_type")
    company_id = fields.Many2one(comodel_name='res.company', related='booking_id.company_id', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        sequences = self.env["ir.sequence"]
        for vals in vals_list:
            service_id = self.env["hotel.service"].browse(int(vals["service_id"]))
            # Check if the 'sequence_id' is not already provided
            if vals.get("sequence_id", _("New")) == _("New"):
                vals["sequence_id"] = sequences.next_by_code(
                    "hotel.booking.service.line"
                ) or _("New")
            if service_id.service_type == "paid":
                vals["state"] = "confirm"
            if service_id.service_type == "free":
                vals["state"] = "done"
        
        records = super(HotelBookingServiceLine, self).create(vals_list)
        for record in records:
            booking = record.booking_id
            if not booking:
                continue

            product = record.service_id.product_id or self.env.ref("hotel_management_system.product_hotel_service")
            section_name = "Alloted Services"

            # Booking Line Section
            if not booking.booking_line_ids.filtered(lambda l: l.display_type == "line_section" and l.name == section_name):
                self.env["hotel.booking.line"].create({
                    "name": section_name,
                    "booking_id": booking.id,
                    "display_type": "line_section",
                })

            rec_name = f"{record.service_id.name} - ({record.service_id.service_type})"
            booking_line = self.env['hotel.booking.line'].create({
                "name": rec_name,
                'booking_id': booking.id,
                'product_id': product.id,
                'price': record.amount,
                'booking_days': 1,
                'tax_ids': [(6, 0, product.taxes_id.ids)],
                'service_line_id': record.id,
            })

            service_value = record.service_type == "free"
            for sale_order in booking.sale_order_ids:
                if not sale_order.order_line.filtered(lambda l: l.display_type == "line_section" and l.name == section_name):
                    sale_order.order_line = [(0, 0, {
                        "name": section_name,
                        "display_type": "line_section",
                    })]

                so_line = self.env['sale.order.line'].create({
                    "order_id": sale_order.id,
                    "product_id": product.id,
                    "name": rec_name,
                    "is_free_service": service_value,
                    "price_unit": 0.0 if service_value else record.amount,
                    "tax_id": [(6, 0, product.taxes_id.ids)],
                })
                booking_line.sale_order_line_id = so_line.id
        return records
    
    def unlink(self):
        for record in self:
            booking_lines = self.env['hotel.booking.line'].search([('service_line_id', '=', record.id)])
            for line in booking_lines:
                if line.sale_order_line_id:
                    order = line.sale_order_line_id.order_id
                    sale_order_state = order.state
                    order.state = 'draft'
                    line.sale_order_line_id.unlink()
                    order.state = sale_order_state
                line.unlink()

        return super().unlink()

    def action_completed(self):
        for record in self:
            if record.state in ["draft", "confirm"]:
                record.state = "done"

    def action_service_cancel(self):
        for record in self:
            if record.state in ["draft", "confirm"]:
                record.state = "cancel"
