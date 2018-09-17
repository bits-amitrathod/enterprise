# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class RequestWizard(models.TransientModel):
    _name = "documents.request_wizard"
    _description = "Document Request"

    name = fields.Char()
    tag_ids = fields.Many2many('documents.tag', string="Tags")
    folder_id = fields.Many2one('documents.folder')
    partner_id = fields.Many2one('res.partner', string="Contact")
    owner_id = fields.Many2one('res.users', default=lambda self: self.env.user.id, string="Owner",
                               track_visibility='onchange')

    activity_type_id = fields.Many2one('mail.activity.type',
                                       string="Activity type",
                                       default=lambda self: self.env.ref('documents.mail_documents_activity_data_md',
                                                                         raise_if_not_found=False))
    activity_summary = fields.Char('Summary')
    activity_date_deadline_range = fields.Integer(string='Due Date In')
    activity_date_deadline_range_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Due type', default='days')

    @api.multi
    def request_document(self):
        self.ensure_one()
        attachment = self.env['ir.attachment'].create({
            'name': self.name,
            'type': 'empty',
            'folder_id': self.folder_id.id if self.folder_id else False,
            'tag_ids': [(6, 0, self.tag_ids.ids if self.tag_ids else [])],
            'owner_id': self.owner_id.id if self.owner_id else False,
            'partner_id': self.partner_id.id if self.partner_id else False,
        })

        activity_vals = {
            'summary': "Requested Document",
            'user_id': self.owner_id.id if self.owner_id else self.env.user.id,
            'partner_id': self.partner_id,
            'activity_type_id': self.activity_type_id.id if self.activity_type_id else False,
        }

        if self.activity_date_deadline_range > 0:
            activity_vals['date_deadline'] = fields.Date.context_today(self) + relativedelta(
                **{self.activity_date_deadline_range_type: self.activity_date_deadline_range})

        attachment.activity_schedule(**activity_vals)

