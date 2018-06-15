# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from datetime import datetime

from odoo import models, fields, _

from odoo.exceptions import ValidationError


class SEPADirectDebitXMLWizard(models.TransientModel):
    """ Wizard allowing to download a SDD XML file once it has been generated.
    """
    _name = 'sdd.download.xml.wizard'

    batch_payment_id = fields.Many2one(string='Batch Payment',
                                 comodel_name='account.batch.payment',
                                 readonly=True,
                                 required=True,
                                 help="Batch payment from which the XML has been generated.")

    xml_file = fields.Binary(string='SEPA XML file', related='batch_payment_id.sdd_xml_file', help="Generated XML file")
    xml_filename = fields.Char(string='SEPA XML file name', related='batch_payment_id.sdd_xml_filename', help="Name of the generated XML file")
