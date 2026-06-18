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
from odoo import api, fields, models

class BookingTenureWizard(models.TransientModel):
    _name = 'booking.tenure.wizard'
    _description = "Reschedule Stay Wizard"


    booking_id = fields.Many2one('hotel.booking', required=True)
    check_in = fields.Datetime(required=True)
    check_out = fields.Datetime(required=True)
    warning = fields.Char(readonly=True)
    available = fields.Boolean(default=False, readonly=True)

    @api.onchange('check_in', 'check_out')
    def _onchange_check_dates(self):
        res = self.booking_id.check_selected_rooms_availability(self.check_in, self.check_out)
        self.warning = res['message']
        self.available = res['available']

    def action_confirm_tenure_update(self):
        self.ensure_one()
        self.booking_id.write({
            'check_in': self.check_in,
            'check_out': self.check_out,
        })

        order = self.booking_id.order_id
        if order:
            order.write({
                'hotel_check_in': self.check_in,
                'hotel_check_out': self.check_out,
            })
