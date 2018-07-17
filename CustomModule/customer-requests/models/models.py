# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import logging


_logger = logging.getLogger(__name__)


class SpsCustomer(models.Model):

    _inherit = 'res.partner'

    file = fields.Binary()
    api_secret = fields.Char()
    template_mapper = fields.Many2one('sps.template.mapper')
    customer_sku = fields.Selection((('choice1', 'ABT'), ('choice2', 'KPN'), ('choice3', 'FREE Courier')), string='SKU', store=False)
    required_quantity = fields.Char(string='Required Quantity', store=False, compute='_compute_required_quantity')
    quantity = fields.Char(string='Stock', store=False, compute='_compute_display_name')
    frequency_of_refill = fields.Char(string='Frequency of Refill', store=False, compute='_compute_fref')
    uom = fields.Char(string='Unit Of Measurement', store=False, compute='_compute_uom')

    @api.model
    @api.depends('file', 'template_mapper')
    def _compute_customer_sku(self):
          self.customer_sku = self.template_mapper.customer_sku

    @api.depends('file', 'template_mapper')
    def _compute_required_quantity(self):
        for partner in self:
            partner.required_quantity = partner.template_mapper.required_quantity

    @api.depends('file', 'template_mapper')
    def _compute_display_name(self):
        for partner in self:
            partner.quantity = partner.template_mapper.quantity

    @api.depends('file', 'template_mapper')
    def _compute_fref(self):
        for partner in self:
            partner.frequency_of_refill = partner.template_mapper.frequency_of_refill

    @api.depends('file', 'template_mapper')
    def _compute_uom(self):
        for partner in self:
            partner.uom = partner.template_mapper.uom

    @api.model
    def create(self, vals):
        partner_model = super(SpsCustomer, self).create(vals)
        return partner_model

    @api.multi
    def write(self, vals):
        res = super(SpsCustomer, self).write(vals)
        if res:
            today_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            partner_id = self.id
            sps_customer_template_mapping = {
                'template_field': self.customer_sku,
                'mapping_field': 'customer_sku',
                'customer_id': partner_id,
                'create_uid': 1,
                'create_date': today_date,
                'write_uid': 1,
                'write_date': today_date}
            self.env['sps.template.mapping'].create(sps_customer_template_mapping)
        _logger.info('RES VALUE...... %r', str(res))
        return res
