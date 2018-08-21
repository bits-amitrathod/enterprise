# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import logging


_logger = logging.getLogger(__name__)


class SpsCustomer(models.Model):

    _inherit = 'res.partner'

    file = fields.Binary()
    api_secret = fields.Char()
    document_ids = fields.One2many('sps.cust.uploaded.documents', 'customer_id')
    template_ids = fields.One2many('sps.customer.template', 'customer_id')
    sps_customer_requests = fields.One2many('sps.customer.requests', 'customer_id')


    @api.model
    def create(self, vals):
        partner_model = super(SpsCustomer, self).create(vals)
        return partner_model

    @api.multi
    def write(self, vals):
        res = super(SpsCustomer, self).write(vals)
        return res

    @api.multi
    def import_method(self):
        _logger.info('import method')