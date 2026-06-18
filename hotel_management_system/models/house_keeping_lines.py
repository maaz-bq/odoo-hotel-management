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
from odoo import models, fields, _

class HouseKeepingLines(models.Model):
    _name = "house.keeping.lines"
    _description = "House Keeping Lines"

    item_id = fields.Many2one("house.keeping.items", "Item")
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
        ],
        default="draft",
        string="Status",
        readonly=True,
    )
    remarks = fields.Char("Remarks")
    house_keeping_id = fields.Many2one(
        "hotel.housekeeping", "House Keeping", readonly=True
    )
    
    def action_in_progress(self):
        for line in self:
            line.status = "in_progress"
            if line.house_keeping_id.state != "in_progress":
                line.house_keeping_id.state = "in_progress"

    def action_completed(self):
        self.status = "completed"
        for parent_house_keeping in self.house_keeping_id:
            remaining_uncompleted_tasks = (
                parent_house_keeping.house_keeping_line_ids.filtered(
                    lambda task: task.status in ["draft", "in_progress"]
                )
            )
            if not remaining_uncompleted_tasks:
                parent_house_keeping.state = "completed"

    def action_draft(self):
        for rec in self:
            rec.status = "draft"
