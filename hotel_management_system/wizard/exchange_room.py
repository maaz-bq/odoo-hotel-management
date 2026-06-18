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
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class ExchangeRoom(models.TransientModel):
    _name = "exchange.room"
    _description = "Exchange rooms if available"

    booking_line_id = fields.Many2one(
        'hotel.booking.line', string='Reference No')
    price = fields.Float(related='booking_line_id.price',
                         string="Current Price")
    available_room_ids = fields.Many2many('product.product')
    exchange_room = fields.Many2one('product.product', string='Exchange Room')
    exchange_price = fields.Float(
        related="exchange_room.lst_price", string="Exchange Price")
    price_difference = fields.Float(
        compute='_compute_price_difference', store=True, string="Price Difference")
    warning = fields.Text(string="Warning In Exchange Rooms",
                          compute="_compute_warning", store=True, readonly=False)

    @api.depends('exchange_room')
    def _compute_price_difference(self):
        for rec in self:
            if rec.exchange_room:
                booking_line = self.env['hotel.booking.line'].browse(
                    self._context.get("active_ids"))
                rec.price_difference = booking_line.price - rec.exchange_room.lst_price

                adult = sum(
                    1 for guest in rec.booking_line_id.guest_info_ids if guest.is_adult)
                child = len(rec.booking_line_id.guest_info_ids) - adult

                if adult > rec.exchange_room.max_adult or child > rec.exchange_room.max_child:
                    rec.warning = "The number of current guests exceeds the room's allowed limit."
                else:
                    rec.warning = ""

    @api.onchange('booking_line_id')
    def booking_line_compute(self):
        booking_line = self.env['hotel.booking.line'].browse(
            self._context.get("active_ids"))
        self.booking_line_id = booking_line
        booking = booking_line.booking_id
        self.available_room_ids = booking.get_available_room_products(
            booking.check_in, booking.check_out, booking.hotel_id.id, room_exchange=True)

    def action_exchange_room(self):
        booking_line = self.env['hotel.booking.line'].browse(
            self._context.get("active_ids"))
        line = booking_line.sale_order_line_id
    
        if not (booking_line or line):
            return
        order = booking_line.sale_order_line_id.order_id

        if order:
            posted_invoice_count = len(
                order.invoice_ids.filtered(lambda i: i.state == 'posted'))

            if (posted_invoice_count):
                raise ValidationError(
                    _('You cannot exchange a room if an invoice or delivery has been created for the related sale order.'))
            elif (self.exchange_room):
                extra_cost = 0
                if booking_line.guest_info_ids:
                    total_guests = len(booking_line.guest_info_ids)
                    if total_guests > booking_line.base_occupancy:
                        extra_guests = total_guests-booking_line.base_occupancy
                        extra_cost = extra_guests * booking_line.extra_charge_per_person
                booking_line.with_context(bypass_for_exchange_room=True).write(
                    {
                        "product_id": self.exchange_room.id,
                        "price": self.exchange_room.lst_price + extra_cost
                    }
                )
                order.with_context(bypass_for_exchange_room=True).write(
                    {'state': 'draft'})
                line.unlink()
                sale_order_line = self.env['sale.order.line'].create({
                    'order_id': order.id,
                    'product_id': booking_line.product_id.id,
                    'tax_id': [(6, 0, booking_line.tax_ids.ids)],
                    'price_unit': booking_line.price,
                    'product_uom_qty': booking_line.booking_days,
                    'guest_info_ids': [(6, 0, booking_line.guest_info_ids.ids)]
                })
                booking_line.with_context(bypass_for_exchange_room=True).write(
                    {"sale_order_line_id": sale_order_line.id})
                order.with_context(bypass_for_exchange_room=True).write(
                    {'state': 'sale'})
            templ_id = self.env.ref(
                'hotel_management_system.hotel_booking_exchange_id')
            templ_id.send_mail(booking_line.booking_id.id, force_send=True)

            if booking_line.hotel_service_lines:
                hb_object = booking_line.booking_id.manage_alloted_services(is_checkout=False)
                if hb_object:
                    return hb_object
            
            return True
        else:
            return self.env['wk.wizard.message'].genrated_message("Exchange is not possible", name='Message')


class AvailableProduct(models.TransientModel):
    _name = "available.product"
    _description = "Available Rooms"

    name = fields.Char("Room Name")
    room_id = fields.Integer("Room Id", store=True)
    exchange_id = fields.Many2one("exchange.room")
    template_attribute_value_ids = fields.Many2many(
        'product.template.attribute.value', string="Attribute Values")
