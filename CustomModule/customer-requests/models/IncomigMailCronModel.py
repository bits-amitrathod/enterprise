# -*- coding: utf-8 -*-

import email
import logging
import re
import csv
import poplib
import pandas as pd
import random
import string
import os
import html2text
import errno
from collections import namedtuple


from odoo import api, fields, models, tools, _
from odoo.tools import pycompat

from datetime import datetime

try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib

from email.message import Message

_logger = logging.getLogger(__name__)
MAX_POP_MESSAGES = 50
MAIL_TIMEOUT = 60

poplib._MAXLINE = 65536

ATTACHMENT_DIR = "/home/odoouser/attachments/"

INCOMING_EMAIL_ID = "bits.qa10@gmail.com"

class IncomingMailCronModel(models.Model):
    _inherit = 'fetchmail.server'


    @api.multi
    def fetch_mail(self):
        for server in self:

            count, failed = 0, 0

            pop_server = None

            if server.type == 'pop':
                try:
                    while True:
                        pop_server = server.connect()

                        (num_messages, total_size) = pop_server.stat()

                        pop_server.list()

                        for num in range(1, min(MAX_POP_MESSAGES, num_messages) + 1):
                            (header, messages, octets) = pop_server.retr(num)
                            message = (b'\n').join(messages)
                            res_id = None
                            try:

                                if isinstance(message, xmlrpclib.Binary):
                                    message = bytes(message.data)

                                if isinstance(message, pycompat.text_type):
                                    message = message.encode('utf-8')

                                extract = getattr(email, 'message_from_bytes', email.message_from_string)
                                message = extract(message)

                                if not isinstance(message, Message):
                                    message = pycompat.to_native(message)
                                    message = email.message_from_string(message)

                                email_to = tools.decode_message_header(message, 'To')

                                match = re.search(r'[\w\.-]+@[\w\.-]+', email_to)

                                email_to = str(match.group(0))

                                if email_to == INCOMING_EMAIL_ID :

                                    _Attachment = namedtuple('Attachment', ('fname', 'content', 'info'))

                                    attachments = []

                                    body = u''

                                    email_from = tools.decode_message_header(message, 'From')

                                    match = re.search(r'[\w\.-]+@[\w\.-]+', email_from)

                                    email_from = str(match.group(0))

                                    subject = tools.decode_message_header(message, 'Subject')

                                    if message.get_content_maintype() != 'text':

                                        alternative = False

                                        for part in message.walk():

                                            if part.get_content_type() == 'multipart/alternative':
                                                alternative = True

                                            if part.get_content_maintype() == 'multipart':
                                                continue  # skip container

                                            filename = part.get_param('filename', None, 'content-disposition')

                                            if not filename:
                                                filename = part.get_param('name', None)

                                            if filename:

                                                if isinstance(filename, tuple):
                                                    filename = email.utils.collapse_rfc2231_value(filename).strip()

                                                else:
                                                    filename = tools.decode_smtp_header(filename)

                                            encoding = part.get_content_charset()

                                            if filename and part.get('content-id'):
                                                inner_cid = part.get('content-id').strip('><')
                                                attachments.append(_Attachment(filename, part.get_payload(decode=True),
                                                                               {'cid': inner_cid}))
                                                continue

                                            if filename or part.get('content-disposition', '').strip().startswith(
                                                    'attachment'):
                                                attachments.append(
                                                    _Attachment(filename or 'attachment', part.get_payload(decode=True),
                                                                {}))
                                                continue

                                            if part.get_content_type() == 'text/plain' and (
                                                    not alternative or not body):
                                                body = tools.append_content_to_html(body, tools.ustr(
                                                    part.get_payload(decode=True), encoding, errors='replace'),
                                                                                    preserve=True)

                                            elif part.get_content_type() == 'text/html':
                                                body = tools.ustr(part.get_payload(decode=True), encoding,
                                                                  errors='replace')

                                            else:
                                                attachments.append(
                                                    _Attachment(filename or 'attachment', part.get_payload(decode=True),
                                                                {}))

                                        if len(attachments) > 0:

                                            encoding = message.get_content_charset()
                                            plain_text = html2text.HTML2Text()
                                            message_payload = plain_text.handle(
                                                tools.ustr(body, encoding, errors='replace'))

                                            if '- Forwarded message -' in message_payload:
                                                messages = message_payload.split('- Forwarded message -')
                                                total_parts = len(messages)
                                                originator_part = messages[total_parts - 1]
                                                match = re.search(r'[\w\.-]+@[\w\.-]+', originator_part)
                                                if match:
                                                    email_from_domain = re.search("@[\w.]+", email_from).group(0)
                                                    email_to_domain = re.search("@[\w.]+", email_to).group(0)
                                                    if email_to_domain != email_from_domain:
                                                        email_from = None
                                                    else:
                                                        email_from = str(match.group(0))

                                            _logger.info('message payload: %r %r', message_payload, email_from)

                                            if not email_from is None:

                                                users_model = self.env['res.partner'].search(
                                                    [("email", "=", email_from)])

                                                if users_model:

                                                    user_attachment_dir = ATTACHMENT_DIR + str(
                                                        datetime.now().strftime("%d%m%Y")) + "/" + str(
                                                        users_model.id) + "/"

                                                    if not os.path.exists(os.path.dirname(user_attachment_dir)):
                                                        try:
                                                            os.makedirs(os.path.dirname(user_attachment_dir))
                                                        except OSError as exc:
                                                            if exc.errno != errno.EEXIST:
                                                                raise

                                                    mappings = self.env['sps.template.mapping'].search(
                                                        [['customer_id', '=', users_model.id]])

                                                    for attachment in attachments:
                                                        filename = getattr(attachment, 'fname')

                                                        if not filename is None:

                                                            try:
                                                                file_contents_bytes = getattr(attachment, 'content')

                                                                file_path = user_attachment_dir + str(filename)

                                                                file_ref = open(str(file_path), "wb+")
                                                                file_ref.write(file_contents_bytes)
                                                                file_ref.close()

                                                                if str(filename).endswith('.csv'):
                                                                    requests, file_acceptable = self.prase_csv(
                                                                        file_path,
                                                                        mappings)
                                                                    _logger.info('csv requests length : %r',
                                                                                 len(requests))

                                                                elif str(filename).endswith('.xls') or str(
                                                                        filename).endswith('.xlsx'):

                                                                    requests, file_acceptable = self.prase_excel(
                                                                        file_path, mappings)

                                                                    _logger.info('excel requests length : %r',
                                                                                 len(requests))

                                                                else:
                                                                    file_acceptable = False

                                                                error_occured_while_saving_file = False

                                                            except Exception as e:
                                                                _logger.info(str(e))

                                                                error_occured_while_saving_file = True

                                                            if not error_occured_while_saving_file:

                                                                if file_acceptable is None and len(requests) > 0:

                                                                    _logger.info(requests)

                                                                    user_id = users_model.id

                                                                    today_date = datetime.now().strftime(
                                                                        "%Y-%m-%d %H:%M:%S")

                                                                    file_upload_record = {
                                                                        'token': self.random_string_generator(30),
                                                                        'customer_id': users_model.id,
                                                                        'document_name': self.random_string_generator(
                                                                            10),
                                                                        'file_location': file_path,
                                                                        'source': 'email', 'status': 'draft',
                                                                        'create_uid': 1, 'create_date': today_date,
                                                                        'write_uid': 1,
                                                                        'write_date': today_date}

                                                                    file_uploaded_record = self.env[
                                                                        'sps.cust.uploaded.documents'].create(
                                                                        file_upload_record)

                                                                    document_id = file_uploaded_record.id

                                                                    for req in requests:

                                                                        sps_products = self.env[
                                                                            'sps.product'].search(
                                                                            [['customer_id', '=', user_id],
                                                                             ['customer_sku', '=',
                                                                              req['customer_sku']]])

                                                                        if len(sps_products) >= 1:

                                                                            sps_product = sps_products[0]

                                                                            sps_product_id = sps_product.id

                                                                            req.update({'customer_id': user_id,
                                                                                        'product_id': sps_product_id,
                                                                                        'document_id': document_id,
                                                                                        'sps_sku': sps_product.sps_sku,
                                                                                        'uom': sps_product.uom,
                                                                                        'status': 'draft'})

                                                                            sps_customer_request = {
                                                                                'document_id': document_id,
                                                                                'customer_id': user_id,
                                                                                'status': 'draft',
                                                                                'create_uid': 1,
                                                                                'create_date': today_date,
                                                                                'write_uid': 1,
                                                                                'write_date': today_date}

                                                                            for key in req.keys():
                                                                                sps_customer_request.update(
                                                                                    {key: req[key]})

                                                                            self.env[
                                                                                'sps.customer.requests'].create(
                                                                                sps_customer_request)

                                                                        else:
                                                                            _logger.info('Voided Product')
                                                                else:
                                                                    _logger.info(
                                                                        'file is not acceptable or zero records in the file')
                                                        else:
                                                            _logger.info('filename is None')
                                                else:
                                                    _logger.info('user not found for %r', email_from)
                                            else:
                                                _logger.info('domain not matched for forwarded email')
                                        else:
                                            _logger.info("No attachements found")

                                    else:
                                        _logger.info('Not a Multipart email');

                                pop_server.dele(num)

                            except Exception:
                                _logger.info('Failed to process mail from %s server %s.', server.type, server.name, exc_info=True)
                                failed += 1

                            if res_id and server.action_id:
                                server.action_id.with_context({
                                    'active_id': res_id,
                                    'active_ids': [res_id],
                                    'active_model': self.env.context.get("thread_model", server.object_id.model)
                                }).run()
                            self.env.cr.commit()

                        if num_messages < MAX_POP_MESSAGES:
                            break
                        pop_server.quit()
                        _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", num_messages, server.type, server.name, (num_messages - failed), failed)
                except Exception:
                    _logger.info("General failure when trying to fetch mail from %s server %s.", server.type, server.name, exc_info=True)
                finally:
                    if pop_server:
                        pop_server.quit()
            server.write({'date': fields.Datetime.now()})
        return super(IncomingMailCronModel, self).fetch_mail()


    @staticmethod
    def prase_csv(uploaded_file_path, mappings):
        file_acceptable = None
        requests = []
        try:
            with open(uploaded_file_path) as csvfile:
                reader = csv.DictReader(csvfile)
                for record in reader:
                    x = {}
                    for mapping in mappings:
                        x.update({mapping['mapping_field']: record[mapping['template_field']]})
                    requests.append(x)
        except UnicodeDecodeError as ue:
            _logger.info(str(ue))
            file_acceptable = False

        return requests, file_acceptable

    @staticmethod
    def prase_excel(uploaded_file_path, mappings):
        file_acceptable = None
        requests = []
        try:
            data_frame = pd.read_excel(uploaded_file_path)
            columns = list(data_frame)
            for row in data_frame.iterrows():
                index, data = row
                record = data.tolist()
                x = {}
                for mapping in mappings:
                    x.update({mapping['mapping_field']: record[columns.index(mapping['template_field'])] })
                requests.append(x)
        except UnicodeDecodeError as ue:
            file_acceptable = False
            _logger.info(str(ue))
        return requests, file_acceptable

    @staticmethod
    def random_string_generator(size=10, chars=string.ascii_lowercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))



