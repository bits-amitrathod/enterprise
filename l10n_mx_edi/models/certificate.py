# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
import base64
import tempfile
import os
import ssl

from contextlib import closing
from OpenSSL import crypto
from pytz import timezone
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

CER_TO_PEM_CMD = 'openssl x509 -in %s -inform der -outform pem -out %s'
KEY_TO_PEM_CMD = 'openssl pkcs8 -in %s -inform der -outform pem -out %s -passin file:%s'

def unlink_temporary_files(temporary_files):
    for temporary_file in temporary_files:
        try:
            os.unlink(temporary_file)
        except (OSError, IOError):
            _logger.error('Error when trying to remove file %s' % temporary_file)

def convert_cer_to_pem(cer):
    cer_file_fd, cer_file_path = tempfile.mkstemp(suffix='.cer', prefix='edi.mx.tmp.')
    with closing(os.fdopen(cer_file_fd, 'w')) as cer_file:
        cer_file.write(cer)
    cerpem_file_fd, cerpem_file_path = tempfile.mkstemp(suffix='.pem', prefix='edi.mx.tmp.')

    os.popen(CER_TO_PEM_CMD % (cer_file_path, cerpem_file_path))
    with open(cerpem_file_path, 'r') as f:
        cer_pem = f.read()

    unlink_temporary_files([cer_file_path, cerpem_file_path])
    return cer_pem

def convert_key_cer_to_pem(key, password):
    key_file_fd, key_file_path = tempfile.mkstemp(suffix='.key', prefix='edi.mx.tmp.')
    with closing(os.fdopen(key_file_fd, 'w')) as key_file:
        key_file.write(key)
    pwd_file_fd, pwd_file_path = tempfile.mkstemp(suffix='.txt', prefix='edi.mx.tmp.')
    with closing(os.fdopen(pwd_file_fd, 'w')) as pwd_file:
        pwd_file.write(password)
    keypem_file_fd, keypem_file_path = tempfile.mkstemp(suffix='.key', prefix='edi.mx.tmp.')

    os.popen(KEY_TO_PEM_CMD % (key_file_path, keypem_file_path, pwd_file_path))
    with open(keypem_file_path, 'r') as f:
        key_pem = f.read()

    unlink_temporary_files([key_file_path, keypem_file_path, pwd_file_path])
    return key_pem

def str_to_datetime(dt_str, tz=timezone('America/Mexico_City')):
    return tz.localize(fields.Datetime.from_string(dt_str))


class Certificate(models.Model):
    _name = 'l10n_mx_edi.certificate'
    _description = 'SAT Digital Sail'
    _order = "date_start desc, id desc"

    content = fields.Binary(
        string='Certificate',
        help='Certificate in der format',
        required=True,
        stored=True)
    key = fields.Binary(
        string='Certificate Key',
        help='Certificate Key in der format',
        required=True,
        stored=True)
    password = fields.Char(
        string='Certificate Password',
        help='Password for the Certificate Key',
        required=True,
        stored=True)
    serial_number = fields.Char(
        string='Serial number',
        help='The serial number to add to electronic documents',
        readonly=True,
        index=True)
    date_start = fields.Datetime(
        string='Available date',
        help='The date on which the certificate starts to be valid',
        readonly=True)
    date_end = fields.Datetime(
        string='Expiration date',
        help='The date on which the certificate expires',
        readonly=True)

    @api.multi
    def get_data(self):
        '''Return the content (b64 encoded) and the certificate decrypted 
        '''
        self.ensure_one()
        cer = base64.decodestring(self.content)
        cer_pem = convert_cer_to_pem(cer)
        certificate = crypto.load_certificate(crypto.FILETYPE_PEM, cer_pem)
        for to_del in ['\n', ssl.PEM_HEADER, ssl.PEM_FOOTER]:
            cer_pem = cer_pem.replace(to_del, '')
        return cer_pem, certificate

    @api.multi
    def get_mx_current_datetime(self):
        '''Get the current datetime with the Mexican timezone.
        '''
        mexican_tz = timezone('America/Mexico_City')
        mexican_dt = datetime.now(mexican_tz)
        return mexican_dt

    @api.multi
    def get_valid_certificate(self):
        '''Search for a valid certificate that is available and not expired.
        '''
        mexican_dt = self.get_mx_current_datetime()
        for record in self:
            date_start = str_to_datetime(record.date_start)
            date_end = str_to_datetime(record.date_end)
            if mexican_dt >= date_start and mexican_dt <= date_end:
                return record
        return None

    @api.multi
    def get_encrypted_cadena(self, cadena):
        '''Encrypt the cadena using the private key.
        '''
        self.ensure_one()
        key = base64.decodestring(self.key)
        key_pem = convert_key_cer_to_pem(key, self.password)
        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
        cadena_crypted = crypto.sign(private_key, cadena, 'sha1')
        return base64.encodestring(cadena_crypted).replace('\n', '').replace('\r', '')

    @api.multi
    @api.constrains('content', 'key', 'password')
    def _check_date_range(self):
        '''Check the validity of content/key/password and fill the fields
        with the certificate values.
        '''
        mexican_tz = timezone('America/Mexico_City')
        mexican_dt = self.get_mx_current_datetime()
        date_format = '%Y%m%d%H%M%SZ'
        for record in self:
            # Try to decrypt the certificate
            try:
                content, certificate = record.get_data()
                before = mexican_tz.localize(
                    datetime.strptime(certificate.get_notBefore(), date_format))
                after = mexican_tz.localize(
                    datetime.strptime(certificate.get_notAfter(), date_format))
                serial_number = certificate.get_serial_number()
            except Exception as e:
                raise ValidationError(_('The certificate content is invalid.'))
            # Assign extracted values from the certificate
            record.serial_number = ('%x' % serial_number)[1::2]
            record.date_start = before.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            record.date_end = after.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if mexican_dt > after:
                raise ValidationError(_('The certificate is expired since %s') % record.date_end)
            # Check the pair key/password
            try:
                key = base64.decodestring(record.key)
                key_pem = convert_key_cer_to_pem(key, record.password)
                private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
            except Exception as e:
                raise ValidationError(_('The certificate key and/or password is/are invalid.'))
