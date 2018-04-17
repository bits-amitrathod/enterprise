# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class SaleReport(models.Model):
    _inherit = 'sale.report'

    order_id = fields.Many2one(string="Order", comodel_name='sale.order', readonly=True)
    is_abandoned_cart = fields.Boolean(string="Abandoned Cart", readonly=True)

    def _select(self):
        select_term = """
            , s.id as order_id
            , s.date_order <= (timezone('utc', now()) - ((COALESCE(config.value, '1.0') || ' hour')::INTERVAL))
            AND team.team_type = 'website'
            AND s.state = 'draft'
            AND s.partner_id != %s
            AS is_abandoned_cart
        """ % self.env.ref('base.public_partner').id
        return super(SaleReport, self)._select() + select_term

    def _from(self):
        from_term = """
            left join crm_team team on team.id = s.team_id
            left join ir_config_parameter config on config.key = 'website_sale.cart_abandoned_delay'
        """
        return super(SaleReport, self)._from() + from_term

    def _group_by(self):
        group_by_term = """
            , s.id
            , config.value
            , team.team_type
            """
        return super(SaleReport, self)._group_by() + group_by_term
