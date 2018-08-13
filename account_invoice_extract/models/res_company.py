# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    show_ocr_option_selection = fields.Selection([
        ('no_send', 'Never send an attachment to IAP'),
        ('manual_send', "Don't send attachments to iap automatically, but let the user send it manually"),
        ('auto_send', 'automatically send attachments to iap')], string="Send mode on invoices attachments",
        required=True, default='manual_send')