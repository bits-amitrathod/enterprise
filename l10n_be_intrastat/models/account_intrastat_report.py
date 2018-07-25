# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class IntrastatReport(models.AbstractModel):
    _inherit = 'account.intrastat.report'

    def _get_reports_buttons(self):
        res = super(IntrastatReport, self)._get_reports_buttons()
        if self.env.user.company_id.country_id == self.env.ref('base.be'):
            res += [{'name': _('Export (XML)'), 'action': 'print_xml'}]
        return res

    @api.model
    def get_xml(self, options):
        ''' Create the xml export.

        :param options: The report options.
        :return: The xml export file content.
        '''
        date_from, date_to, company_ids, incl_arrivals, incl_dispatches, extended = self._decode_options(options)

        if len(company_ids) != 1:
            raise ValidationError(_('One and only one company must be selected.'))

        company = self.env['res.company'].browse(company_ids[0])

        cache = {}

        # create in_vals corresponding to invoices with cash-in
        in_vals = []
        if incl_arrivals:
            query, params = self._prepare_query(
                date_from, date_to, company_ids=[company.id], invoice_types=('in_invoice', 'out_refund'))
            self._cr.execute(query, params)
            in_vals = self._cr.dictfetchall()
            [self._fill_missing_values(v, cache) for v in in_vals]

        # create out_vals corresponding to invoices with cash-out
        out_vals = []
        if incl_dispatches:
            query, params = self._prepare_query(
                date_from, date_to, company_ids=[company.id], invoice_types=('out_invoice', 'in_refund'))
            self._cr.execute(query, params)
            out_vals = self._cr.dictfetchall()
            [self._fill_missing_values(v, cache) for v in out_vals]

        return self.env.ref('l10n_be_intrastat.intrastat_report_export_xml').render({
            'company': company,
            'in_vals': in_vals,
            'out_vals': out_vals,
            'extended': extended,
        })
