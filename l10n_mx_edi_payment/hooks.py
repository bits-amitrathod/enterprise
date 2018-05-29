# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from odoo.tools import DEFAULT_SERVER_TIME_FORMAT


def post_init_hook(cr, registry):
    """Set the newly created fields values in payments created before the
    installation of this module
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    payments = env['account.payment'].search(
        [('l10n_mx_edi_time_payment', '=', False),
         ('l10n_mx_edi_expedition_date', '=', False)])
    for payment in payments:
        date_mx = env['l10n_mx_edi.certificate'].sudo().get_mx_current_datetime() # noqa
        payment.l10n_mx_edi_time_payment = date_mx.strftime(
            DEFAULT_SERVER_TIME_FORMAT)
        payment.l10n_mx_edi_expedition_date = date_mx
