from odoo import fields, models


class IotDevice(models.Model):
    _inherit = 'iot.device'

    quality_point_ids = fields.One2many('quality.point', 'device_id')


class QualityPoint(models.Model):
    _inherit = "quality.point"

    device_id = fields.Many2one('iot.device', ondelete='restrict')
