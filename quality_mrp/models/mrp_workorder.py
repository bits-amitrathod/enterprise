# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpProductionWorkcenterLine(models.Model):
    _inherit = "mrp.workorder"

    check_ids = fields.One2many('quality.check', 'workorder_id')
    quality_check_todo = fields.Boolean(compute='_compute_check')
    quality_check_fail = fields.Boolean(compute='_compute_check')
    quality_alert_ids = fields.One2many('quality.alert', 'workorder_id')
    quality_alert_count = fields.Integer(compute="_compute_quality_alert_count")

    @api.multi
    def _compute_check(self):
        for workorder in self:
            todo = False
            fail = False
            for check in workorder.check_ids:
                if check.quality_state == 'none':
                    todo = True
                elif check.quality_state == 'fail':
                    fail = True
                if fail and todo:
                    break
            workorder.quality_check_fail = fail
            workorder.quality_check_todo = todo

    @api.multi
    def _compute_quality_alert_count(self):
        for workorder in self:
            workorder.quality_alert_count = len(workorder.quality_alert_ids)

    @api.multi
    def open_quality_alert_wo(self):
        self.ensure_one()
        action = self.env.ref('quality.quality_alert_action_check').read()[0]
        action['context'] = {
            'default_product_id': self.product_id.id,
            'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
            'default_workorder_id': self.id,
            'default_production_id': self.production_id.id,
            'default_workcenter_id': self.workcenter_id.id,
            }
        action['domain'] = [('id', 'in', self.quality_alert_ids.ids)]
        action['views'] = [(False, 'tree'),(False,'form')]
        if self.quality_alert_count == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.quality_alert_ids.id
        return action

    @api.multi
    def button_quality_alert(self):
        self.ensure_one()
        action = self.env.ref('quality.quality_alert_action_check').read()[0]
        action['views'] = [(False, 'form')]
        action['context'] = {
            'default_product_id': self.product_id.id,
            'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
            'default_workorder_id': self.id,
            'default_production_id': self.production_id.id,
            'default_workcenter_id': self.workcenter_id.id,
        }
        return action

    @api.multi
    def _create_checks(self):
        for wo in self:
            production = wo.production_id
            points = self.env['quality.point'].search([('operation_id', '=', wo.operation_id.id),
                                                       ('picking_type_id', '=', production.picking_type_id.id),
                                                       '|', ('product_id', '=', production.product_id.id),
                                                       '&', ('product_id', '=', False), ('product_tmpl_id', '=', production.product_id.product_tmpl_id.id)])
            for point in points:
                if point.check_execute_now():
                    self.env['quality.check'].create({'workorder_id': wo.id,
                                                  'point_id': point.id,
                                                  'team_id': point.team_id.id,
                                                  'product_id': production.product_id.id,
                                                 })

    @api.multi
    def record_production(self):
        self.ensure_one()
        if any([(x.quality_state == 'none') for x in self.check_ids]):
            raise UserError(_('You still need to do the quality checks!'))
        if self.check_ids:
            #Check if you can attribute the lot to the checks
            if (self.production_id.product_id.tracking != 'none') and self.final_lot_id:
                checks_to_assign = self.check_ids.filtered(lambda x: not x.lot_id)
                if checks_to_assign:
                    checks_to_assign.write({'lot_id': self.final_lot_id.id})
        super(MrpProductionWorkcenterLine, self).record_production()
        if self.qty_producing > 0:
            self._create_checks()

    @api.multi
    def check_quality(self):
        self.ensure_one()
        checks = self.check_ids.filtered(lambda x: x.quality_state == 'none')
        if checks:
            action_rec = self.env.ref('quality.quality_check_action_small')
            if action_rec:
                action = action_rec.read([])[0]
                action['context'] = dict(self.env.context, active_model='mrp.workorder')
                action['res_id'] = checks[0].id
                return action
