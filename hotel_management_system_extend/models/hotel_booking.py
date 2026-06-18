# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import models


class HotelBooking(models.Model):
    _inherit = "hotel.booking"

    def _ensure_booking_line_guests(self):
        GuestInfo = self.env["guest.info"]
        for booking in self:
            partner = booking.partner_id
            for line in booking.booking_line_ids.filtered(lambda booking_line: not booking_line.guest_info_ids):
                sale_line = line.sale_order_line_id
                sale_guests = sale_line.guest_info_ids if sale_line else GuestInfo
                if sale_guests:
                    sale_guests.write({"booking_line_id": line.id})
                    continue
                if partner:
                    GuestInfo.create(
                        {
                            "name": partner.name or "Guest",
                            "booking_line_id": line.id,
                            "sale_order_line_id": sale_line.id if sale_line else False,
                            "age": 18,
                        }
                    )

    def manage_check_in_out_based_on_restime(self):
        self._ensure_booking_line_guests()
        super().manage_check_in_out_based_on_restime()
        for booking in self:
            if not booking.check_in or not booking.check_out:
                continue
            if booking.check_out <= booking.check_in:
                booking.check_out = booking.check_in + timedelta(days=1)
            if booking.order_id:
                booking.order_id.with_context(bypass_checkin_checkout=True).write(
                    {
                        "hotel_check_in": booking.check_in,
                        "hotel_check_out": booking.check_out,
                    }
                )

    def action_confirm_booking(self):
        self._ensure_booking_line_guests()
        return super().action_confirm_booking()
