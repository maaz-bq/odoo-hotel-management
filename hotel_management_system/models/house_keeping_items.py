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
from odoo import models, fields

class HouseKeepingItems(models.Model):
    _name = "house.keeping.items"
    _description="Items Alloted to House Keeper"
    
    name = fields.Char('Name', required=True)
    product_id = fields.Many2one('product.product', 'Product')
    is_auto_added = fields.Boolean(
        string="Add to Housekeeping?",
        help="If checked, this item will be automatically included as a line in the housekeeping record when created."
    )
    
