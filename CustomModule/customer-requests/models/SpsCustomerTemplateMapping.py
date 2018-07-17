# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SpsCustomerTemplateMapping(models.Model):

    _name = 'sps.template.mapping'

    template_field = fields.Char()
    mapping_field = fields.Char()
    customer_id = fields.Integer()

