# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from os.path import join, dirname, realpath

from odoo import tools


def post_init_hook(cr, registry):
    _load_product_sat_catalog(cr, registry)
    _assign_codes_uom(cr, registry)


def _load_product_sat_catalog(cr, registry):
    """Import CSV data as it is faster than xml and because we can't use
    noupdate anymore with csv"""
    csv_path = join(dirname(realpath(__file__)), 'data',
                    'l10n_mx_edi_cfdi_33.product.sat.code.csv')
    csv_file = open(csv_path, 'rb')
    cr.copy_expert(
        """COPY l10n_mx_edi_product_sat_code(code, name, applies_to, active)
           FROM STDIN WITH DELIMITER '|'""", csv_file)
    # Create xml_id, to allow make reference to this data
    cr.execute(
        """INSERT INTO ir_model_data
           (name, res_id, module, model)
           SELECT concat('prod_code_sat_', code), id, 'l10n_mx_edi_cfdi_33', 'l10n_mx_edi.product.sat.code'
           FROM l10n_mx_edi_product_sat_code""")


def _assign_codes_uom(cr, registry):
    """Assign the codes in UoM of each data, this is here because the data is
    created in the last method"""
    tools.convert.convert_file(
        cr, 'l10n_mx_edi_cfdi_33', 'data/product_data.xml', None, mode='init',
        kind='data')
