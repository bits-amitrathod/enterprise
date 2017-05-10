# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _, fields
from odoo.tools import pycompat
from odoo.tools.xml_utils import check_with_xsd

MX_NS_REFACTORING = {
    'catalogocuentas__': 'catalogocuentas',
    'BCE__': 'BCE',
}

CFDICOA_TEMPLATE = 'l10n_mx_reports.cfdi11coa'
CFDICOA_XSD = 'l10n_mx_reports/data/xsd/%s/cfdi11coa.xsd'
CFDICOA_XSLT_CADENA = 'l10n_mx_reports/data/xslt/%s/CatalogoCuentas_1_1.xslt'


class MXReportAccountCoa(models.AbstractModel):
    _name = "l10n_mx.coa.report"
    _inherit = "l10n_mx.trial.report"
    _description = "Mexican Chart of Account Report"

    filter_date = None
    filter_comparison = None
    filter_cash_basis = None
    filter_all_entries = None
    filter_hierarchy = None
    filter_journals = None

    def get_templates(self):
        templates = super(MXReportAccountCoa, self).get_templates()
        #use the main template instead of the trial balance with 2 header lines
        templates['main_template'] = 'account_reports.main_template'
        return templates

    def get_columns_name(self, options):
        return [{'name': ''}, {'name': _('Nature')}]

    def get_lines(self, options, line_id=None):
        options['coa_only'] = True
        return self._post_process({}, {}, options, [])

    def get_coa_dict(self, options):
        xml_data = self.get_lines(options)
        accounts = []
        account_lines = [l for l in xml_data
                         if l.get('caret_options') == 'account.account']
        account_obj = self.env['account.account']
        for line in account_lines:
            account = account_obj.browse(line['id'])
            tag = account.tag_ids.filtered(lambda r: r.color == 4)
            if not tag:
                continue
            accounts.append({
                'code': tag.name[:6],
                'number': account.code,
                'name': account.name,
                'level': '2',
                'nature': tag.nature,
            })
        chart = {
            'vat': self.env.user.company_id.vat or '',
            'month': str(fields.date.today().month).zfill(2),
            'year': fields.date.today().year,
            'accounts': accounts
        }
        return chart

    def get_xml(self, options):
        qweb = self.env['ir.qweb']
        version = '1.1'
        values = self.get_coa_dict(options)
        cfdicoa = qweb.render(CFDICOA_TEMPLATE, values=values)
        for key, value in pycompat.items(MX_NS_REFACTORING):
            cfdicoa = cfdicoa.replace(key, value + ':')

        check_with_xsd(cfdicoa, CFDICOA_XSD % version)
        return cfdicoa
