# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class MrpProductionWorkcenterLine(models.Model):
    _inherit = "mrp.workorder"

    ip = fields.Char(related='current_quality_check_id.point_id.device_id.iot_id.ip')
    identifier = fields.Char(related='current_quality_check_id.point_id.device_id.identifier')


