# coding: utf-8

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_mx_edi_addenda = fields.Many2one('ir.ui.view',
        string='Addenda',
        help='A view representing the addenda',
        domain=[('l10n_mx_edi_addenda_flag', '=', True)])
    l10n_mx_edi_colony = fields.Char(string='Colony Name')
    l10n_mx_edi_locality = fields.Char(string='Locality Name')
