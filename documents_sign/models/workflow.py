from odoo import models, fields, api, exceptions


class WorkflowActionRuleSign(models.Model):
    _inherit = ['documents.workflow.rule']

    has_business_option = fields.Boolean(default=True, compute='_get_business')
    create_model = fields.Selection(selection_add=[('sign.template', "Signature template")])

    def create_record(self, attachments=None):
        rv = super(WorkflowActionRuleSign, self).create_record(attachments=attachments)
        if self.create_model == 'sign.template':
            for attachment in attachments:
                create_values = {
                    'name': attachment.name,
                    'attachment_id': attachment.id,
                }
                new_obj = self.env[self.create_model].create(create_values)

                this_attachment = attachment
                if attachment.res_model or attachment.res_id:
                    this_attachment = attachment.copy()

                this_attachment.res_model = self.create_model
                this_attachment.res_id = new_obj.id
        return rv
