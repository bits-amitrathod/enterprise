# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Lead(models.Model):
    _inherit = 'crm.lead'

    won = fields.Boolean('Is Won', compute='_compute_won', store=True)
    lost = fields.Boolean('Is Lost', compute='_compute_lost', store=True)

    days_to_convert = fields.Float('Days To Convert', compute='_compute_days_to_convert', store=True)

    days_exceeding_closing = fields.Float('Exceeded Closing Days', compute='_compute_days_exceeding_closing', store=True)

    @api.multi
    @api.depends('active', 'stage_id.probability')
    def _compute_won(self):
        for lead in self:
            lead.won = lead.active and lead.stage_id.probability == 100

    @api.multi
    @api.depends('active', 'probability')
    def _compute_lost(self):
        for lead in self:
            lead.lost = not lead.active and lead.probability == 0

    @api.multi
    @api.depends('date_conversion', 'create_date')
    def _compute_days_to_convert(self):
        for lead in self:
            if lead.date_conversion:
                lead.days_to_convert = (fields.Datetime.from_string(lead.date_conversion) - fields.Datetime.from_string(lead.create_date)).days

    @api.multi
    @api.depends('date_deadline', 'date_closed')
    def _compute_days_exceeding_closing(self):
        for lead in self:
            if lead.date_closed and lead.date_deadline:
                lead.days_exceeding_closing = (fields.Datetime.from_string(lead.date_deadline) - fields.Datetime.from_string(lead.date_closed)).days

