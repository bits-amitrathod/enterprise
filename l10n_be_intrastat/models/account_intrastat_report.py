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
        date_from, date_to, journal_ids, incl_arrivals, incl_dispatches, extended = self._decode_options(options)

        company = self.env.user.company_id

        cache = {}

        # create in_vals corresponding to invoices with cash-in
        in_vals = []
        if incl_arrivals:
            query, params = self._prepare_query(
                date_from, date_to, journal_ids=journal_ids, invoice_types=('in_invoice', 'out_refund'))
            self._cr.execute(query, params)
            query_res = self._cr.dictfetchall()
            in_vals = self._fill_missing_values(query_res, cache)

        # create out_vals corresponding to invoices with cash-out
        out_vals = []
        if incl_dispatches:
            query, params = self._prepare_query(
                date_from, date_to, journal_ids=journal_ids, invoice_types=('out_invoice', 'in_refund'))
            self._cr.execute(query, params)
            query_res = self._cr.dictfetchall()
            out_vals = self._fill_missing_values(query_res, cache)

        return self.env.ref('l10n_be_intrastat.intrastat_report_export_xml').render({
            'company': company,
            'in_vals': in_vals,
            'out_vals': out_vals,
            'extended': extended,
        })
