# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # To this case the options in selection field are in Spanish, because are
    # only three options and We need that value to set in the CFDI
    l10n_mx_cfdi_tax_type = fields.Selection(
        [('Tasa', 'Tasa'),
         ('Cuota', 'Cuota'),
         ('Exento', 'Exento')], 'Factor Type',
        help='The CFDI version 3.3 have the attribute "TipoFactor" in the tax '
        'lines. In it is indicated the factor type that is applied to the '
        'base of the tax.')
