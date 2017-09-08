# coding: utf-8

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_mx_edi_addenda = fields.Many2one('ir.ui.view',
        string='Addenda',
        help='A view representing the addenda',
        domain=[('l10n_mx_edi_addenda_flag', '=', True)])
    l10n_mx_edi_addenda_doc = fields.Html(string='Addenda Documentation',
        help='''How should be done the adenda for this customer (try to put human readable information here to help the
        invoice people to fill properly the fields in the invoice)''')
    l10n_mx_edi_colony = fields.Char(string='Colony Name')
    l10n_mx_edi_locality = fields.Char(string='Locality Name')


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    l10n_mx_edi_code = fields.Char(
        'Code', help='Code defined to this position. If this record will be '
        'used as fiscal regime to CFDI, here must be assigned the code '
        'defined to this fiscal regime in the SAT catalog')
