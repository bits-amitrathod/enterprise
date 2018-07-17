# -*- coding: utf-8 -*-
from odoo import http

import logging

import os

import json
import random
import string
from datetime import datetime
import csv

from odoo.http import request

import errno

from werkzeug import FileStorage

from odoo import exceptions
from odoo.http import Controller, request, route
from odoo.addons.bus.models.bus import dispatch

import pandas as pd


_logger = logging.getLogger(__name__)

UPLOAD_DIR = "/home/odoouser/uploads/"


class FileUploadController(Controller):

    @http.route('/api/upload/', type='http', auth='public', csrf=False)
    def upload_api(self, **post):

        response = None

        try:

            username = post['username']

            password = post['password']

            file_storage = FileStorage(post['file'])

        except Exception as e:

            response = {'errorCode': 1, 'message': 'Bad Request'}

        if response is None:

            user_api_settings = request.env['res.partner'].sudo().search([['email', '=', username], ['api_secret', '=', password]])

            if len(user_api_settings) == 1:

                user_id = user_api_settings[0].id

                directory_path = UPLOAD_DIR + str(datetime.now().strftime("%d%m%Y")) + "/" + str(
                    user_id) + "/"

                file_name = FileUploadController.random_string_generator(10)

                if not os.path.exists(os.path.dirname(directory_path)):
                    try:
                        os.makedirs(os.path.dirname(directory_path))
                    except OSError as exc:
                        if exc.errno != errno.EEXIST:
                            raise

                uploaded_file_path = str(directory_path + file_name)

                file_storage.save(uploaded_file_path)

                mappings = request.env['sps.template.mapping'].sudo().search([['customer_id', '=', user_id]])

                if len(mappings) == 0:
                    mappings = request.env['sps.template.mapping'].sudo().search([['customer_id', '=', None]])

                _logger.info(' Mapping list : %r ',  mappings)

                requests, file_acceptable = self.prase_csv(uploaded_file_path,mappings)

                if not file_acceptable is None:
                    requests, file_acceptable = FileUploadController.prase_excel(uploaded_file_path, mappings)

                if file_acceptable is None and len(requests) > 0:

                    today_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    file_upload_record = {'token': FileUploadController.random_string_generator(30), 'customer_id': user_id,
                                          'document_name': FileUploadController.random_string_generator(10),
                                          'file_location': uploaded_file_path, 'source': 'api', 'status': 'draft',
                                          'create_uid': 1, 'create_date': today_date, 'write_uid': 1,
                                          'write_date': today_date}

                    file_uploaded_record = request.env['sps.cust.uploaded.documents'].sudo().create(file_upload_record)

                    document_id = file_uploaded_record.id

                    ref = str(document_id) + "_" + file_uploaded_record.token

                    response = {'errorCode': 0, 'message': 'success', 'ref': ref}

                    for req in requests:

                        sps_products = request.env['sps.product'].sudo().search(
                            [['customer_id', '=', user_id], ['customer_sku', '=', req['customer_sku']]])

                        if len(sps_products) >= 1:

                            sps_product = sps_products[0]

                            sps_product_id = sps_product.id

                            req.update({'customer_id': user_id, 'product_id': sps_product_id, 'document_id': document_id,
                                    'sps_sku': sps_product.sps_sku, 'uom': sps_product.uom,
                                    'status': 'draft'})

                            sps_customer_request = {'document_id': document_id, 'customer_id': user_id, 'status': 'draft',
                                                'create_uid': 1, 'create_date': today_date, 'write_uid': 1,
                                                'write_date': today_date}

                            for key in req.keys():
                                sps_customer_request.update({key: req[key]})

                            request.env['sps.customer.requests'].sudo().create(sps_customer_request)

                        else:
                            _logger.info('Voided Product')
                else:
                    _logger.info('file is not acceptable')
                    response = {'errorCode': 2, 'message': 'File is not CSV nor Excel' }

            else:
                response = {'errorCode': 2, 'message': 'UnAuthorized Access'}

        return json.JSONEncoder().encode(response)

    @staticmethod
    def random_string_generator(size=10, chars=string.ascii_lowercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def prase_csv(self, uploaded_file_path, mappings):
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
                    x.update({mapping['mapping_field']: record[columns.index(mapping['template_field'])]})
                requests.append(x)
        except UnicodeDecodeError as ue:
            file_acceptable = False
            _logger.info(str(ue))
        return requests, file_acceptable
