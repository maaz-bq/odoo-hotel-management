# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import models, fields

class CrmTeam(models.Model):
    _inherit = "crm.team"

    is_housekeeping = fields.Boolean(
        'Is Housekeeping Team', default=False)
    auto_assignment_housekeeping = fields.Boolean(
        "Automatic Assignment", default=False)
    assign_method_housekeeping = fields.Selection([
        ('randomly', 'Each user is assigned an equal number of tasks'),
        ('balanced', 'Each user has an equal number of open tasks')],
        string='Assignment Method', default='randomly', required=True,
        help="New tasks will automatically be assigned to the team members that are available, "
        "according to their working hours and their time off.")
