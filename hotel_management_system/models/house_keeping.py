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
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HouseKeeping(models.Model):
    _name = "hotel.housekeeping"
    _description = "House Keeping"
    _rec_name = "sequence_id"

    sequence_id = fields.Char(
        string="Sequence",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _("New"),
    )
    assign_to = fields.Many2one("res.users", string="Assign To")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
        ],
        default="draft",
        string="state",
    )
    booking_line_id = fields.Many2one(
        "hotel.booking.line", string="Room")
    booking_id = fields.Many2one(related="booking_line_id.booking_id")
    image_1920 = fields.Image(string="Image", related="assign_to.image_1920")
    room_id = fields.Many2one("product.product", string="Rooms", required=True, related='booking_line_id.product_id')
    responsible = fields.Many2one("res.users", string="Responsible")
    team_id = fields.Many2one("crm.team", string="Team")

    schedule_date = fields.Datetime("Schedule Date")
    deadline = fields.Datetime("Deadline")
    house_keeping_line_ids = fields.One2many(
        'house.keeping.lines', 'house_keeping_id')
    company_id = fields.Many2one(comodel_name='res.company', related='booking_id.company_id', store=True)

    def action_in_progress(self):
        for housekeeping in self:
            if not housekeeping.assign_to:
                raise UserError(_("Please set the Assign To first."))
            
            housekeeping.state = "in_progress"
            
            if housekeeping.house_keeping_line_ids:
                housekeeping.house_keeping_line_ids.write({'status': 'in_progress'})


    def action_completed(self):
        for housekeeping in self:
            if housekeeping.state != "in_progress":
                raise UserError(
                    _("Housekeeping must be in progress to mark as completed.")
                )

            housekeeping.state = "completed"

            if housekeeping.house_keeping_line_ids:
                housekeeping.house_keeping_line_ids.write({'status': 'completed'})


    def action_draft(self):
        self.state = "draft"
        for rec in self.house_keeping_line_ids:
            rec.status = "draft"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "company_id" in vals:
                self = self.with_company(vals["company_id"])
            if vals.get("sequence_id", _("New")) == _("New"):
                seq_date = (
                    fields.Datetime.context_timestamp(
                        self, fields.Datetime.to_datetime(vals["check_in"])
                    )
                    if "check_in" in vals
                    else None
                )
                vals["sequence_id"] = self.env["ir.sequence"].next_by_code(
                    "hotel.housekeeping", sequence_date=seq_date
                ) or _("New")
        return super().create(vals_list)

    def create_housekeeping_items(self):
        items = self.env["house.keeping.items"].sudo().search([('is_auto_added','=', True)])
        if items:
            recs = []
            for item in items:
                rec = {
                    "item_id": item.id,
                    "house_keeping_id": self.id,
                    "remarks": item.name
                }
                recs.append(rec)
            self.env["house.keeping.lines"].create(recs)

    def auto_assign_housekeeping(self):
        is_allocation = self.team_id.auto_assignment_housekeeping
        allocation_type = self.team_id.assign_method_housekeeping
        check_auto = self.env["ir.config_parameter"].sudo().get_param("hotel_management_system.housekeeping_config")        
        if is_allocation and check_auto != "none":
            if allocation_type == "randomly":
                last_assigned_user = self.env['hotel.housekeeping'].search([('team_id', '=', self.team_id.id), ('assign_to', '!=', False)],
                                                                           order='create_date desc, id desc', limit=1).assign_to
                index = 0
                if last_assigned_user and last_assigned_user.id in self.team_id.member_ids.ids:
                    previous_index = self.team_id.member_ids.ids.index(last_assigned_user.id)
                    index = (previous_index + 1) % len(self.team_id.member_ids.ids)
                self.assign_to = self.env['res.users'].browse(self.team_id.member_ids.ids[index])
            else:
                ticket_count_data = self.env['hotel.housekeeping']._read_group([(
                    'assign_to', 'in', self.team_id.member_ids.ids), ('team_id', '=', self.team_id.id)], ['assign_to'], ['__count'])
                open_ticket_per_user_map = dict.fromkeys(self.team_id.member_ids.ids, 0)
                open_ticket_per_user_map.update((user.id, count) for user, count in ticket_count_data)
                result= self.env['res.users'].browse(min(open_ticket_per_user_map, key=open_ticket_per_user_map.get))
                self.assign_to = result.id  
