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
from odoo.exceptions import ValidationError, UserError
from markupsafe import Markup
from datetime import datetime
import pytz

STATUS_DOMAIN = ("status_bar", "not in", ["initial", "cancel", "checkout"])

class SaleOrder(models.Model):
    _inherit = "sale.order"

    hotel_check_in = fields.Datetime(
        "Check In", required=False, help="Date of the arrival."
    )
    booking_id = fields.Many2one("hotel.booking", "Booking")
    hotel_id = fields.Many2one("hotel.hotels", "Hotel")
    hotel_check_out = fields.Datetime(
        "Check Out", required=False, help="Date of the departure."
    )
    booking_count = fields.Integer("Booking count", copy=False)
    is_room_type = fields.Boolean("Is Room Type")
    booking_line_id = fields.Many2one("hotel.booking.line", "Room No")

    @api.constrains("hotel_check_in", "hotel_check_out")
    def _check_validity_check_in_check_out(self):
        """verifies if check_in is earlier than check_out."""
        for booking in self:
            if not self.env.context.get('bypass_checkin_checkout', False):
                if (
                    booking.hotel_check_in
                    and booking.hotel_check_in < fields.Datetime.today()
                ):
                    raise ValidationError(
                        _('"Check In" time cannot be earlier than Today time.')
                    )
                if booking.hotel_check_in and booking.hotel_check_out:
                    if booking.hotel_check_out <= booking.hotel_check_in:
                        raise ValidationError(
                            _('"Check Out" time cannot be earlier than "Check In" time.')
                        )

    def _pricelist_validation_for_booking_service(self):
        if self.booking_line_id:
            return (
                True
                if self.pricelist_id == self.booking_line_id.booking_id.pricelist_id
                else False
            )

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if self.booking_count > 0:
            res.update({"booking_count": self.booking_count})
        return res
    
    @api.onchange('hotel_id')
    def _onchange_hotel_id(self):
        room_products = self.order_line.filtered(lambda line: line.product_id.is_room_type)
        if room_products:
            raise ValidationError("Cannot change the Hotel if there are sale order lines with Room products. Please remove them first.")

    def action_add_rooms(self):
        self.ensure_one()
        return self.booking_id._action_add_rooms(self.hotel_check_in, self.hotel_check_out, self.hotel_id.id, sale_order_id=self.id)
    
    def action_confirm(self):
        """
        Returns
        True
        """
        for rec in self:
            flag = rec._pricelist_validation_for_booking_service()
            if flag is False:
                raise ValidationError(
                    _(
                        "A different price list has been detected, please remember that pricelist will be same as booking pricelist!"
                    )
                )

        room_type_booking_line = self.order_line.filtered("product_id.product_tmpl_id.is_room_type")
        if room_type_booking_line:
            booked_rooms = room_type_booking_line.mapped("product_id")
            available_rooms = self.env['hotel.booking'].get_available_room_products(
                self.hotel_check_in, self.hotel_check_out, self.hotel_id.id
            )

            # Convert to sets for efficient difference check
            booked_room_ids = set(booked_rooms.ids)
            available_room_ids = set(available_rooms.ids)

            unavailable_room_ids = booked_room_ids - available_room_ids
            if not unavailable_room_ids:
                    booking_vals = {
                        "partner_id": rec.partner_id.id,
                        "order_id": rec.id,
                        "check_in": rec.hotel_check_in,
                        "check_out": rec.hotel_check_out,
                        "booking_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "discount": line.discount,
                                    "product_id": line.product_id.id,
                                    "price": line.price_unit,
                                    "tax_ids": line.tax_id,
                                    "subtotal_price": line.price_subtotal,
                                    "guest_info_ids": line.guest_info_ids,
                                    "sale_order_line_id": line.id,
                                },
                            )
                            for line in rec.order_line
                            if line.product_id.product_tmpl_id.is_room_type
                        ],
                        "pricelist_id": rec.pricelist_id.id if rec.pricelist_id else False,
                        "booking_reference": "sale_order",
                        "amount_untaxed": rec.amount_untaxed,
                        "tax_amount": rec.amount_tax,
                        "total_amount": rec.amount_total,
                        "status_bar": "initial",
                        "hotel_id": rec.hotel_id.id,
                    }

                    if rec.booking_id:
                        rec.message_post(
                            body=Markup(
                                _(
                                    "<span class='text-danger'>A booking already exists for this order. Updating the existing booking.</span>"
                                )
                            )
                        )
                        rec.booking_id.booking_line_ids.unlink()
                        rec.booking_id.write(booking_vals)
                        rec.booking_id.manage_check_in_out_based_on_restime()
                    else:
                        booking = rec.env["hotel.booking"].create(booking_vals)
                        booking.manage_check_in_out_based_on_restime()
                        rec.write(
                            {
                                "booking_id": booking.id,
                                "booking_count": rec.booking_count + 1 if rec.booking_count else 1,
                            }
                        )
            else:
                rec.message_post(
                    body=Markup(
                        _(
                            "<span class='text-danger'>Some rooms are not available !</span>"
                        )
                    )
                )
                return rec.env["wk.wizard.message"].genrated_message(
                    "<span class='text-danger' style='font-weight:bold;'>Some rooms are not available!</span>",
                    name="Warning",
                )

            if (
                rec.env["ir.config_parameter"]
                .sudo()
                .get_param("hotel_management_system.auto_confirm_booking")
            ) and rec.amount_paid == rec.amount_total and rec.booking_id:
                rec.booking_id.action_confirm_booking()

        return super(SaleOrder, self).action_confirm()
    
    def action_cancel(self):
        booking_id = self.booking_id
        if booking_id.status_bar == 'allot':
            raise ValidationError(_('The existing hotel booking associated to this order is either Alloted. If is it alloted then make sure to Checkout it first. '))
        if booking_id.status_bar != "allot":
            booking_id.status_bar = "cancel"
        return super(SaleOrder, self).action_cancel()
    
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if self.env.context.get("bypass_for_exchange_room"):
            return res
        for rec in self.filtered(lambda booking: booking.booking_id):
            for so_ol in rec.order_line:
                hotel_booking_line = self.env['hotel.booking.line'].search([('sale_order_line_id','=',so_ol.id)],limit=1)
                if hotel_booking_line:
                    hotel_booking_line.write({
                                                "product_id": so_ol.product_id.id,
                                                "discount": so_ol.discount,
                                                "price": so_ol.price_unit,
                                                "tax_ids": so_ol.tax_id,
                                                "subtotal_price": so_ol.price_subtotal,
                                                "guest_info_ids": so_ol.guest_info_ids
                                            })
        return res

    def action_view_booking(self):
        """Open Booking view

        Returns
        -------
        Open view
        """
        booking_id = 0
        result = self.env["ir.actions.act_window"]._for_xml_id(
            "hotel_management_system.action_hotel_booking_menu"
        )
        # choose the view_mode accordingly
        if self.booking_count == 1 or self.booking_line_id:
            res = self.env.ref("hotel_management_system.hotel_booking_view_form", False)
            form_view = [(res and res.id or False, "form")]
            if "views" in result:
                result["views"] = form_view + [
                    (state, view) for state, view in result["views"] if view != "form"
                ]
            else:
                result["views"] = form_view
            if self.booking_line_id:
                booking_id = self.booking_line_id
            else:
                booking_id = self.env["hotel.booking"].search(
                    [("order_id", "=", self.id)]
                )
            result["res_id"] = booking_id.id
        else:
            result = {"type": "ir.actions.act_window_close"}
        return result

    @api.onchange("booking_line_id")
    def _onchange_booking_line(self):
        if self.booking_line_id:
            self.partner_id = self.booking_line_id.booking_id.partner_id.id
            self.hotel_check_in = self.booking_line_id.booking_id.check_in
            self.hotel_check_out = self.booking_line_id.booking_id.check_out

    def change_hotel_check_in_out(self, check_in_out_date):
        if self.website_id and self.website_id.checkout_hours:
            checkout_hours = self.website_id.checkout_hours
        else:
            checkout_hours = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("hotel_management_system.checkout_hours")
                or 12.00
            )
        checkout_time_format = "{0:02.0f}:{1:02.0f}".format(
            *divmod(float(checkout_hours) * 60, 60)
        )
        tz = pytz.timezone(self.env.context.get('tz') or 'UTC')
        required_time = datetime.strptime(checkout_time_format, "%H:%M").time()
        check_in_date = check_in_out_date.date()
        combine_time_check_in = tz.localize(
            datetime.combine(check_in_date, required_time)
        )
        return combine_time_check_in.astimezone(pytz.utc).replace(tzinfo=None)

    # BLOCKED: _onchange_check_in_out has been intentionally disabled (see README.md
    # Customization Checklist). Uncomment below to restore check-in/out onchange behavior.
    # @api.onchange("hotel_check_in", "hotel_check_out")
    # def _onchange_check_in_out(self):
    #     '''
    #     - New Check-in and Check-out validations.
    #     - Changing order_line > 'product_oum_qty' as per the check-in and check-out days.
    #     '''
    #     today = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    #     for order in self:

    #         if order.hotel_check_in:
    #             order.hotel_check_in = order.change_hotel_check_in_out(order.hotel_check_in)

    #         if order.hotel_check_out:
    #             if order.hotel_check_in and order.hotel_check_out < order.hotel_check_in:
    #                 raise UserError("Check-out date cannot be before Check-in date.")
    #             order.hotel_check_out = order.change_hotel_check_in_out(order.hotel_check_out)
        
    #     if self.hotel_id and self.order_line and self.hotel_check_in and self.hotel_check_out:
    #         for line in self.order_line:
    #             if line.product_template_id.is_room_type:
    #                 line.product_uom_qty = (self.hotel_check_out - self.hotel_check_in).days
    
    payment_ids = fields.One2many('account.payment','sale_order_id', string='Payments')
    paid_amount=fields.Float(string='Paid Amount',compute='_compute_paid_amount')
    total_payment=fields.Integer(string='Total Amount',compute='_compute_total_payment')
    balance_amount=fields.Float(string='Balance Amount',compute='_compute_balance_amount')

    def _compute_total_payment(self):
        total_payment= len(self.payment_ids.ids)
        self.total_payment=total_payment
    
    def _compute_balance_amount(self):
        for rec in self:
            balance_amount=rec.amount_total - rec.paid_amount
            self.balance_amount=balance_amount

    def _compute_paid_amount(self):
        amount=0.0
        for rec in self.payment_ids:
            amount+=rec.currency_id._convert(rec.amount, self.currency_id, self.company_id)
        self.paid_amount=amount

    def action_register_payment(self):

        amount=self.amount_total-self.paid_amount
        journal=self.env['account.journal'].search([('type', 'in', ['cash', 'bank'])])

        return {
            'name': _('Advance Payment'),
            'res_model': 'account.payment',
            'view_mode': 'form',
            'views': [(self.env.ref('hotel_management_system.view_form_amount_payment').id, 'form')],
            'context': {
                'default_amount':amount,
                'default_currency_id':self.currency_id.id,
                'default_partner_id': self.partner_id.id,
                'default_move_journal_types': ['bank', 'cash'],
                'default_partner_type': 'customer',
                'default_sale_order_id':self.id,
                'default_suitable_journal_ids':journal.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
        
    def action_show_payment(self):
            ctx=dict(self._context)
            ctx['sale_order_id']=self.id

            return {
                "type":"ir.actions.act_window",
                'name':'Payments',
                'res_model':'account.payment',
                'domain':[('sale_order_id','=',self.id)],
                'view_mode':'list,form',
                'target':'self'
                }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        for order in self:
            if order.state not in ('draft', 'cancel'):
                raise UserError(_(
                    "You can not delete a sent quotation or a confirmed sales order."
                    " You must first cancel it."))

            if order.state=='draft' and order.payment_ids.ids:
                raise UserError(_(
                    "You can not delete a Paid order."
                   ))
    
    def _get_default_payment_link_values(self):
        res=super(SaleOrder,self)._get_default_payment_link_values()
        amount=self.amount_total-self.paid_amount
        res['amount']=amount
        return res

    def get_portal_last_transaction(self):
        self.ensure_one()
        if self.balance_amount > 0:
            return self.env["payment.transaction"]

        return super().get_portal_last_transaction()

    # Tax Totals Summary 
    @api.depends_context('lang')
    @api.depends(
        'order_line.price_subtotal',
        'currency_id',
        'company_id',
        'payment_term_id',
        'booking_id.hotel_service_lines.amount',
        'booking_id.hotel_service_lines.service_type',
        'paid_amount', 'balance_amount'
    )
    def _compute_tax_totals(self):
        super()._compute_tax_totals()

        for order in self:
            if order.booking_id:
                tax_totals = order.tax_totals or {}

                paid_services_total = sum(order.booking_id.hotel_service_lines.filtered(
                    lambda l: l.service_type == "paid").mapped("amount"))

                subtotals = tax_totals.get('subtotals', [])

                insert_index = 1 if len(subtotals) > 1 else len(subtotals)

                if paid_services_total:
                    subtotals.insert(insert_index, {
                        'name': 'Total Paid Services',
                        'base_amount_currency': paid_services_total,
                        'base_amount': paid_services_total,
                        'tax_amount_currency': 0.0,
                        'tax_amount': 0.0,
                        'tax_groups': [],
                    })
                    insert_index += 1

                if order.paid_amount:
                    subtotals.insert(insert_index, {
                        'name': 'Paid Amount',
                        'base_amount_currency': order.paid_amount,
                        'base_amount': order.paid_amount,
                        'tax_amount_currency': 0.0,
                        'tax_amount': 0.0,
                        'tax_groups': [],
                    })
                    insert_index += 1

                if order.balance_amount:
                    subtotals.insert(insert_index, {
                        'name': 'Balance Amount',
                        'base_amount_currency': order.balance_amount,
                        'base_amount': order.balance_amount,
                        'tax_amount_currency': 0.0,
                        'tax_amount': 0.0,
                        'tax_groups': [],
                    })

                tax_totals['subtotals'] = subtotals
                order.tax_totals = tax_totals

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    guest_info_ids = fields.One2many(
        "guest.info", "sale_order_line_id", string="Members"
    )
    is_free_service = fields.Boolean(string="Is Free Service")
    warning = fields.Text(string="Warning For Sale Order Line", compute="_compute_warning", store=True, readonly=False)
    max_child = fields.Integer(related="product_template_id.max_child", string="Max Child")
    max_adult = fields.Integer(related="product_template_id.max_adult", string="Max Adult")
    max_occupancy = fields.Integer(related="product_template_id.max_occupancy", string="Max Occupancy")
    base_occupancy = fields.Integer(related="product_template_id.base_occupancy", string="Base Occupancy")
    extra_charge_per_person = fields.Monetary(related="product_template_id.extra_charge_per_person", string="Extra Charge per person")

    adult_guest = fields.Integer("Adult Guest")
    children_guest = fields.Integer("Child Guest")

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

    @api.onchange('guest_info_ids')
    def update_extra_price(self):
        for line in self:
            extra_cost=0
            if line.guest_info_ids:
                total_guests=len(line.guest_info_ids)
                if total_guests > line.base_occupancy:
                    extra_guests=total_guests-line.base_occupancy
                    if extra_guests > 0:
                        extra_cost=extra_guests*line.extra_charge_per_person
                        base_price = line.order_id.pricelist_id._get_product_price(line.product_id, line.product_uom_qty)
                        line.price_unit  = base_price + extra_cost

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def create_invoices(self):
        for order in self.sale_order_ids:
            if order.booking_count >= 1:
                return self.env["wk.wizard.message"].genrated_message(
                    "<span class='text-danger' style='font-weight:bold;'>Can not create invoice for a booking from the sale order %s directly <br/> Go to the related bookings and create invoice from there!</span>"
                    % order.name,
                    name="Warning",
                )
        return super(SaleAdvancePaymentInv, self).create_invoices()
