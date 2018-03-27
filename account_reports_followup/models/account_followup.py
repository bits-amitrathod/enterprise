# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class ResCompany(models.Model):
    _inherit = "res.company"

    min_days_between_followup = fields.Integer('Minimum days between two follow-ups', help="Use this if you want to be sure than a minimum number of days occurs between two follow-ups.", default=6)


class Followup(models.Model):
    _name = 'account_followup.followup'
    _description = 'Account Follow-up'
    _rec_name = 'name'

    followup_line_ids = fields.One2many('account_followup.followup.line', 'followup_id', 'Follow-up', copy=True, oldname="followup_line")
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self.env['res.company']._company_default_get('account_followup.followup'))
    name = fields.Char(related='company_id.name', readonly=True)

    _sql_constraints = [('company_uniq', 'unique(company_id)', 'Only one follow-up per company is allowed')]


class FollowupLine(models.Model):
    _name = 'account_followup.followup.line'
    _description = 'Follow-up Criteria'
    _order = 'delay'

    name = fields.Char('Follow-Up Action', required=True, translate=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of follow-up lines.")
    delay = fields.Integer('Due Days', required=True,
                           help="The number of days after the due date of the invoice to wait before sending the reminder.  Could be negative if you want to send a polite alert beforehand.")
    followup_id = fields.Many2one('account_followup.followup', 'Follow Ups', required=True, ondelete="cascade")
    description = fields.Text('Printed Message', translate=True, default="""
        Dear %(partner_name)s,

Exception made if there was a mistake of ours, it seems that the following amount stays unpaid. Please, take appropriate measures in order to carry out this payment in the next 8 days.

Would your payment have been carried out after this mail was sent, please ignore this message. Do not hesitate to contact our accounting department.

Best Regards,
""")
    send_email = fields.Boolean('Send an Email', help="When processing, it will send an email", default=True)
    send_letter = fields.Boolean('Send a Letter', help="When processing, it will print a letter", default=True)
    manual_action = fields.Boolean('Manual Action', help="When processing, it will set the manual action to be taken for that customer. ", default=False)
    manual_action_note = fields.Text('Action To Do', placeholder="e.g. Give a phone call, check with others , ...")
    manual_action_type_id = fields.Many2one('mail.activity.type', 'Manual Action Type', default=False)
    manual_action_responsible_id = fields.Many2one('res.users', 'Assign a Responsible', ondelete='set null')

    _sql_constraints = [('days_uniq', 'unique(followup_id, delay)', 'Days of the follow-up levels must be different')]

    @api.constrains('description')
    def _check_description(self):
        for line in self:
            if line.description:
                try:
                    line.description % {'partner_name': '', 'date':'', 'user_signature': '', 'company_name': ''}
                except:
                    raise Warning(_('Your description is invalid, use the right legend or %% if you want to use the percent character.'))


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    followup_line_id = fields.Many2one('account_followup.followup.line', 'Follow-up Level')
    followup_date = fields.Date('Latest Follow-up', index=True)


class ResPartner(models.Model):
    _inherit = "res.partner"

    payment_responsible_id = fields.Many2one('res.users', ondelete='set null', string='Follow-up Responsible',
                                             help="Optionally you can assign a user to this field, which will make him responsible for the action.",
                                             track_visibility="onchange", copy=False, company_dependent=True)

    def get_partners_in_need_of_action(self, overdue_only=False):
        return self.get_partners_in_need_of_action_and_update()

    def _compute_followup_lines(self):
        followup_id = 'followup_id' in self.env.context and self.env.context['followup_id'] or self.env['account_followup.followup'].search([('company_id', '=', self.env.user.company_id.id)]).id
        if not followup_id:
            raise Warning(_('No follow-up is defined for the company "%s".\n Please define one.') % self.env.user.company_id.name)

        if not followup_id:
            return {}

        current_date = datetime.date.today()
        self.env.cr.execute(
            "SELECT id, delay "\
            "FROM account_followup_followup_line "\
            "WHERE followup_id=%s "\
            "ORDER BY delay", (followup_id,))

        previous_level = None
        fups = {}
        for result in self.env.cr.dictfetchall():
            delay = datetime.timedelta(days=result['delay'])
            delay_in_days = result['delay']
            fups[previous_level] = (current_date - delay, result['id'], delay_in_days)
            previous_level = result['id']

        fups[previous_level] = (current_date - delay, previous_level, delay_in_days)
        return fups

    def get_followup_html(self):
        options = {
            'partner_id': self.id,
            'followup_level': self.get_followup_level() or False,
            'keep_summary': True
        }
        return self.env['account.followup.report'].with_context(print_mode=True, lang=self.lang or self.env.user.lang).get_html(options)

    @api.multi
    def get_followup_level(self):
        self.ensure_one()
        current_date = datetime.date.today()
        if self.payment_next_action_date and self.payment_next_action_date > current_date.strftime(DEFAULT_SERVER_DATE_FORMAT):
            return False

        fups = self._compute_followup_lines()
        level = None
        for aml in self.unreconciled_aml_ids:
            if aml.company_id == self.env.user.company_id:
                index = aml.followup_line_id.id or None
                followup_date = fups[index][0]
                next_level = fups[index][1]
                delay = fups[index][2]
                if (aml.date_maturity and aml.date_maturity <= followup_date.strftime(DEFAULT_SERVER_DATE_FORMAT)) or (current_date <= followup_date):
                    if level is None or level[1] < delay:
                        level = (next_level, delay)
        return level

    @api.model
    def get_partners_in_need_of_action_and_update(self):
        current_date = datetime.date.today()
        fups = self._compute_followup_lines()
        partners_ids = []
        partners_to_skip = self.env['res.partner'].search([('payment_next_action_date', '>', current_date.strftime(DEFAULT_SERVER_DATE_FORMAT))])

        for record in self.env['res.partner'].search([('id', 'not in', partners_to_skip.ids)]):
            for aml in record.unreconciled_aml_ids:
                if aml.company_id == self.env.user.company_id:
                    index = aml.followup_line_id.id or None
                    followup_date = fups[index][0]
                    if (aml.date_maturity and aml.date_maturity <= followup_date.strftime(DEFAULT_SERVER_DATE_FORMAT)) or (current_date <= followup_date):
                        if record.id not in partners_ids:
                            partners_ids.append(record.id)
                            continue
        return self.browse(partners_ids)

    @api.multi
    def update_next_action(self, options=False):
        if not options or 'next_action_date' not in options or 'next_action_type' not in options:
            return
        next_action_date = options['next_action_date'][0:10]
        today = datetime.date.today()
        fups = self._compute_followup_lines()
        for partner in self:
            if options['next_action_type'] == 'manual':
                partner.change_next_action(next_action_date)
            partner.payment_next_action_date = next_action_date
            for aml in partner.unreconciled_aml_ids:
                index = aml.followup_line_id.id or None
                followup_date = fups[index][0]
                next_level = fups[index][1]
                if (aml.date_maturity and aml.date_maturity <= followup_date.strftime(DEFAULT_SERVER_DATE_FORMAT)) or (aml.date and aml.date <= followup_date.strftime(DEFAULT_SERVER_DATE_FORMAT)):
                    aml.write({'followup_line_id': next_level, 'followup_date': today})
