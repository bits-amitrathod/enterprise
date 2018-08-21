# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging


_logger = logging.getLogger(__name__)

class SpsCustomerUploadedDocument(models.Model):

    _name = 'sps.cust.uploaded.documents'
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    request_ids = fields.One2many('sps.customer.requests', 'document_id')
    token = fields.Char()
    document_name = fields.Char()
    file_location = fields.Char()
    source = fields.Char()
    status = fields.Char()

    @api.multi
    def load(self, import_fields, data):
        _logger.info('fields %r ' , import_fields)

