# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class Report(models.Model):
    _inherit = 'report'

    @api.model
    def get_html(self, docids, report_name, data=None):
        try:
            return super(Report, self).get_html(docids, report_name, data)
        except UserError as e:
            if not data.get('studio'):
                raise
            _logger.warning("Cannot edit report %r with studio: %s", report_name, e)
            return ''
