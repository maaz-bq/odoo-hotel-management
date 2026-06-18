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
from datetime import datetime
from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import datetime, time
from odoo.osv import expression
import pytz
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_room_type = fields.Boolean("Is Room Type")
    max_adult = fields.Integer("Max Adult", default=1)
    max_child = fields.Integer("Max Children", default=1)
    max_infants = fields.Integer("Max Infants", default=1)
    base_occupancy = fields.Integer("Base Occupancy", default=2)
    service_ids = fields.Many2many("hotel.service", string="Services")
    facility_ids = fields.Many2many("hotel.facility", string="Facility")
    product_website_description = fields.Text("Product Website Description")
    room_policy = fields.Html("Room Policy")
    count = fields.Integer("Visit Count")
    hotel_id = fields.Many2one(
        "hotel.hotels",
        string="Hotel",
        domain="[('company_id', 'in', [company_id or current_company_id, False])]",
        ondelete="set null"
    )

    # max_occupancy = fields.Integer("Max Occupancy", default=10)
    max_occupancy = fields.Integer("Max Occupancy", compute="_compute_max_occupancy")
    extra_charge_per_person = fields.Monetary(string="Extra Charge Per Person")

    def reset_trending_room(self):
        # use sql or orm to set count to 0
        rec = (
            self.env["product.template"].sudo().search([(("is_room_type", "=", True))])
        )
        rec.write({"count": 0})

    # -------------------------------------------------------------------------
    # USING IN DEMO DATA
    # -------------------------------------------------------------------------
    @api.model
    def get_room_multiline_policy_description(self):
        description = """
                    <ol><li><p>Check-in and check-out times: hotels have set check-in and check-out times
                    that guests must follow. typically check-in
                    time is in the afternoon, and check-out time is in the morning.</p></li><li><p>Occupancy
                    limits: Hotel rooms have a maximum occupancy limit, which means that only a certain
                    number of people are allowed to stay in the room. This is often determined by the number
                    of beds in the room.</p></li><li><p>Smoking policy: Hotels have a strict no-smoking policy,
                    which means that smoking is not allowed in the rooms or anywhere else on the property. If you
                    are caught smoking, you may be charged a fee or asked to leave.</p></li><li><p>Pet policy:
                    Hotels allow pets, while others do not. If a hotel allows pets, there may be a fee or restrictions
                    on the size or breed of pet allowed.</p></li><li><p>Damage policy: Guests are responsible for any
                    damage caused to the hotel room during their stay. If any damage is found after the guest checks out,
                    the hotel may charge the guest for the repairs.</p></li><li><p>Noise policy: Guests are expected to
                    keep noise levels to a minimum to avoid disturbing other guests. Hotels have quiet hours during
                    which noise must be kept to a minimum.</p></li><li><p>Payment policy: Most hotels require a credit card
                    or other form of payment at the time of booking or check-in. Hotels may require a deposit or hold on
                    the credit card in case of any incidental charges.</p></li></ol>
                """
        room_type_product_ids = self.search([("is_room_type", "=", True)])
        room_type_product_ids.write({"room_policy": description})

    def fetch_data_for_room(self, **kwargs):
        """fetching room information for dashboard
        Returns -> dict Room Data """

        room_record = self.read(["name", "max_adult", "max_child"])
        selected_date = (
            str(kwargs["selected_date"].get("day"))
            + "/"
            + str(kwargs["selected_date"].get("month"))
            + "/"
            + str(kwargs["selected_date"].get("year"))
        )
        datetime_date = datetime.strptime(selected_date, "%d/%m/%Y")

        if datetime_date.date() < fields.Date.today():
            available_rooms = self.env["product.product"]
        else:
            _, available_rooms = self.env[
                "hotel.booking"
            ].get_booked_and_available_rooms(datetime_date, self.id)

        room_record[0].update(
            {
                "service": self.sudo().service_ids.mapped("name"),
                "Facility": self.sudo().facility_ids.mapped("name"),
                "Price": (
                    (self.list_price, self.currency_id.symbol)
                    if self.currency_id.position == "after"
                    else (self.currency_id.symbol, self.list_price)
                ),
                "room_variant_data": available_rooms.read(["display_name"]),
            }
        )

        b_ids = self.env["hotel.booking"].search(
            [("booking_line_ids.product_tmpl_id", "=", self.id)]
        )

        return {
            "room_record": room_record,
            "b_ids": b_ids.ids,
        }

    @api.constrains("max_adult")
    def _check_max_adult(self):
        for record in self:
            if record.max_adult < 1:
                raise UserError("Adult must be 1 or more than...")

    @api.model
    def _search_get_detail(self, website, order, options):
        hotel_id = 0
        result = super()._search_get_detail(website, order, options)

        if options.get("hotel_id", False):
            hotel_id = options.get("hotel_id")

        if hotel_id:
            result["base_domain"].append([("hotel_id", "=", hotel_id)])
        return result
    
    @api.depends('max_child','max_adult','max_infants')
    def _compute_max_occupancy(self):
        for rec in self:
            rec.max_occupancy =  rec.max_child + rec.max_adult + rec.max_infants

class ProductProduct(models.Model):
    _inherit = "product.product"

    # used to compute the room availability
    booking_line_ids = fields.One2many("hotel.booking.line", "product_id")

    is_available_today = fields.Boolean(
        compute="_compute_is_available_today",
        string="Is Available Today",
    )

    @api.depends(
        "booking_line_ids.check_out",
        "booking_line_ids.check_in",
        "booking_line_ids.product_id",
        "booking_line_ids.status_bar",
    )
    def _compute_is_available_today(self):
        today = fields.Datetime.now()
        checkout_hours = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("hotel_management_system.checkout_hours")
                or 12.0
            )
        checkout_time_format = "{0:02.0f}:{1:02.0f}".format(
                *divmod(float(checkout_hours)* 60, 60)
            )
        required_time = datetime.strptime(
            checkout_time_format, "%H:%M").time()
        start_of_today = datetime.combine(today, required_time)
        end_of_today = datetime.combine(today, required_time)

        for record in self:
            if not record.booking_line_ids or not record.booking_line_ids.filtered(
                lambda line: line.status_bar in ["confirm", "allot"]
            ):
                record.is_available_today = True
            else:
                in_between_lines = record.booking_line_ids.filtered(
                    lambda line: line.check_in and line.check_out and line.check_in <= start_of_today <= line.check_out
                )

                if in_between_lines:
                    record.is_available_today = not any(
                        line.status_bar in ["confirm", "allot"]
                        for line in in_between_lines
                    )
                elif record.booking_line_ids.filtered(
                    lambda line: start_of_today >= line.check_out if line.check_out else None
                ) or record.booking_line_ids.filtered(
                    lambda line: start_of_today <= line.check_in if line.check_in else None
                ):
                    record.is_available_today = True

    def action_book_room(self):
        """
        Special Action Method: For opening booking for view (For Room Dashboard)
        """
        self.ensure_one()
        guest = self.env["guest.info"].create({
            "name": "Guest",
            "gender": "male",
            "age": 18,
        })
        booking_line = self.env["hotel.booking.line"].create({
            "product_id": self.id,
            "product_tmpl_id": self.product_tmpl_id.id,
            "guest_info_ids": [(6, 0, [guest.id])],
            "price": self.lst_price,
        })
        return {
            "name": "Book Room",
            "view_mode": "form",
            "res_model": "hotel.booking",
            "type": "ir.actions.act_window",
            "context": {
                "default_hotel_id": self.product_tmpl_id.hotel_id.id,
                "default_booking_line_ids": [(6, 0, [booking_line.id])],
                "skip_hotel_change_validation": True,
            },
            "target": "current",
        }

    def action_view_room_bookings(self):
        """
        -> Special Action Method: For opening bookings list view (For Room Dashboard)
        """
        self.ensure_one()
        return {
            "name": f"Bookings for {self.display_name}",
            "type": "ir.actions.act_window",
            "res_model": "hotel.booking",
            "view_mode": "list,form",
            "target": "current",
            "domain": [("booking_line_ids.product_id", "=", self.id)],
        }

class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    website_visible = fields.Boolean("Is Visible on Website", default=True)
