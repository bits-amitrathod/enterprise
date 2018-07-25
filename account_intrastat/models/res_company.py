# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    region_id = fields.Many2one('account.intrastat.code', string='Intrastat region',
        domain="[('type', '=', 'region'), '|', ('country_id', '=', None), ('country_id', '=', country_id)]")
    intrastat_transport_mode_id = fields.Many2one('account.intrastat.code', string='Default Transport Mode',
        domain="[('type', '=', 'transport')]")
    incoterm_id = fields.Many2one('account.incoterms', string='Default incoterm for Intrastat',
        help='International Commercial Terms are a series of predefined commercial terms used in international transactions.')
