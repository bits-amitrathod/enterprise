# -*- coding: utf-8 -*-
from odoo import http

import logging

import os

import random
import string
from datetime import datetime
import csv
import collections

import json

from odoo import http



try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat, misc

import errno

from werkzeug import FileStorage

from odoo.http import Controller, request, route

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
        except Exception:
            response = dict(errorCode=1, message='Bad Request')
        if response is None:
            user_api_settings = request.env['res.partner'].sudo().search(
                [('email', '=', username), ('api_secret', '=', password)])
            if len(user_api_settings) == 1:
                user_id = user_api_settings[0].id
                directory_path = UPLOAD_DIR + str(datetime.now().strftime("%d%m%Y")) + "/" + str(user_id) + "/"
                file_name = FileUploadController.random_string_generator(10) + request.params['file'].filename
                if not os.path.exists(os.path.dirname(directory_path)):
                    try:
                        os.makedirs(os.path.dirname(directory_path))
                    except OSError as exc:
                        if exc.errno != errno.EEXIST:
                            raise
                uploaded_file_path = str(directory_path + file_name)
                file_storage.save(uploaded_file_path)

                mapping_field_list = list(request.env['sps.customer.template'].sudo().fields_get().keys())
                mapping_field_list = [mapping_field for mapping_field in mapping_field_list if
                                      mapping_field.startswith('mf_')]
                templates_list = request.env['sps.customer.template'].sudo().search(
                    [['customer_id', '=', user_id], ['template_status', '=', 'Active']])
                mappings = []
                if len(templates_list) > 0:
                    mappings, non_mapped_columns = FileUploadController._get_column_mappings(mapping_field_list,
                                                                                             templates_list,
                                                                                             uploaded_file_path)
                if len(mappings) == 0:
                    response = dict(errorCode=4, message='Template Not Found')
                else:
                    requests, file_acceptable = FileUploadController._parse_csv(uploaded_file_path, mappings, non_mapped_columns)
                    if not file_acceptable is None:
                        requests, file_acceptable = FileUploadController._parse_excel(uploaded_file_path, mappings,
                                                                                      non_mapped_columns)
                    if file_acceptable is None and len(requests) > 0:
                        today_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        file_upload_record = dict(token=FileUploadController.random_string_generator(30),
                                                  customer_id=user_id,
                                                  document_name=FileUploadController.random_string_generator(10),
                                                  file_location=uploaded_file_path, source='api', status='draft',
                                                  create_uid=1, create_date=today_date, write_uid=1,
                                                  write_date=today_date)
                        file_uploaded_record = request.env['sps.cust.uploaded.documents'].sudo().create(
                            file_upload_record)
                        document_id = file_uploaded_record.id
                        ref = str(document_id) + "_" + file_uploaded_record.token
                        response = dict(errorCode=0, message='File Uploaded Successfully', ref=ref)
                        # if user_api_settings.sku_preconfig
                        _logger.info('user_api_settings.sku_preconfig %r', user_api_settings.sku_preconfig)
                        _logger.info('user_api_settings.sku_postconfig %r', user_api_settings.sku_postconfig)
                        for req in requests:
                            sps_products = request.env['sps.product'].sudo().search(
                                [['customer_id', '=', user_id], ['customer_sku', '=', req['customer_sku']]])
                            high_priority_product = False
                            if len(sps_products) >= 1:
                                sps_product = sps_products[0]
                                sps_product_id = sps_product.product_id.id
                                sps_customer_product_priority = request.env[
                                    'sps.customer.product.priority'].sudo().search(
                                    [['product_id', '=', sps_product_id], ['customer_id', '=', user_id],
                                     ['product_priority', '=', 0]])
                                if sps_customer_product_priority or (not user_api_settings.priority is None and user_api_settings.priority == 0):
                                    high_priority_product = True
                                    req.update(dict(product_id=sps_product_id, status='Inprocess'))
                                else:
                                    req.update(dict(product_id=sps_product_id, status='New'))
                            else:
                                req.update(dict(product_id=None, status='Voided'))
                            sps_customer_request = dict(document_id=document_id, customer_id=user_id, create_uid=1,
                                                        create_date=today_date, write_uid=1, write_date=today_date)
                            for key in req.keys():
                                sps_customer_request.update({key: req[key]})
                            saved_sps_customer_request = request.env['sps.customer.requests'].sudo().create(
                                sps_customer_request)
                            if high_priority_product:
                                self.send_sps_customer_request_for_processing(saved_sps_customer_request)
                    else:
                        _logger.info('file is not acceptable')
                        response = dict(errorCode=2, message='Invalid File extension')
            else:
                response = dict(errorCode=3, message='UnAuthorized Access')

        return json.JSONEncoder().encode(response)

    @staticmethod
    def _get_column_mappings(mapping_field_list, templates_list, file_path):
        column_mappings = []
        non_selected_columns = []
        for customer_template in templates_list:
            if customer_template.non_selected_columns:
                non_selected_columns = customer_template.non_selected_columns.split(',')
            mapped_columns = []
            for mapping_field in mapping_field_list:
                if customer_template[mapping_field]:
                    mapped_columns.append(dict(template_field=customer_template[mapping_field], mapping_field=mapping_field))
            selected_columns = [mapped_column['template_field'] for mapped_column in mapped_columns]
            template_column_list = non_selected_columns + selected_columns
            file_extension = file_path[file_path.rindex('.') + 1:]
            if file_extension == 'xls' or file_extension == 'xlsx':
                book = xlrd.open_workbook(file_path)
                columns = FileUploadController._read_xls_book(book)[0]
            elif file_extension == 'csv':
                columns = FileUploadController._read_columns_from_csv(file_path)
            compare = lambda x, y: collections.Counter(x) == collections.Counter(y)
            if compare(template_column_list, columns):
                column_mappings = mapped_columns
                break
        return column_mappings, non_selected_columns

    @staticmethod
    def _read_xls_book(book, read_data=False):
        sheet = book.sheet_by_index(0)
        data = []
        for row in pycompat.imap(sheet.row, range(sheet.nrows)):
            values = []
            for cell in row:
                if cell.ctype is xlrd.XL_CELL_NUMBER:
                    is_float = cell.value % 1 != 0.0
                    values.append(
                        pycompat.text_type(cell.value)
                        if is_float
                        else pycompat.text_type(int(cell.value))
                    )
                elif cell.ctype is xlrd.XL_CELL_DATE:
                    is_datetime = cell.value % 1 != 0.0
                    dt = datetime(*xlrd.xldate.xldate_as_tuple(cell.value, book.datemode))
                    values.append(
                        dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        if is_datetime
                        else dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    )
                elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                    values.append(u'True' if cell.value else u'False')
                elif cell.ctype is xlrd.XL_CELL_ERROR:
                    raise ValueError(
                        ("Error cell found while reading XLS/XLSX file: %s") %
                        xlrd.error_text_from_code.get(
                            cell.value, "unknown error code %s" % cell.value)
                    )
                else:
                    values.append(cell.value)
            data.append(values)
            if not read_data:
                break
        return data

    @staticmethod
    def _read_columns_from_csv(file_path):
        column_row = []
        try:
            with open(file_path) as csvfile:
                reader = csv.DictReader(csvfile)
                for record in reader:
                    column_row.extend(record)
                    break
        except UnicodeDecodeError as ue:
            _logger.info(str(ue))
        return column_row

    @staticmethod
    def random_string_generator(size=10, chars=string.ascii_lowercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    @staticmethod
    def _parse_csv(uploaded_file_path, mappings, non_mapped_columns):
        file_acceptable = None
        requests = []
        try:
            with open(uploaded_file_path) as csvfile:
                reader = csv.DictReader(csvfile)
                for record in reader:
                    un_mapped_data = {}
                    for non_mapped_column in non_mapped_columns:
                        if record[non_mapped_column]:
                            un_mapped_data.update(
                                {non_mapped_column: record[non_mapped_column]})
                    x = {'un_mapped_data': json.dumps(un_mapped_data)}
                    for mapping in mappings:
                        mapping_field = str(mapping['mapping_field'])
                        if mapping_field.startswith('mf_'):
                            x.update({mapping_field[3:] : record[mapping['template_field']]})
                        else:
                            x.update({mapping_field : record[mapping['template_field']]})
                    requests.append(x)
        except UnicodeDecodeError as ue:
            _logger.info(str(ue))
            file_acceptable = False
        return requests, file_acceptable

    @staticmethod
    def _parse_excel(uploaded_file_path, mappings, non_mapped_columns):
        file_acceptable = None
        requests = []
        try:
            book = xlrd.open_workbook(uploaded_file_path)
            excel_data_rows_with_columns = FileUploadController._read_xls_book(book, read_data=True)
            if len(excel_data_rows_with_columns) > 1:
                excel_data_rows = [excel_data_rows_with_columns[idx] for idx in
                                   range(1, len(excel_data_rows_with_columns) - 1)]
                excel_columns = excel_data_rows_with_columns[0]
                for excel_data_row in excel_data_rows:
                    un_mapped_data = {}
                    for non_mapped_column in non_mapped_columns:
                        if excel_columns.index(non_mapped_column) >= 0:
                            un_mapped_data.update({ non_mapped_column : excel_data_row[excel_columns.index(non_mapped_column)]})
                    x = {'un_mapped_data' : json.dumps(un_mapped_data) }
                    for mapping in mappings:
                        mapping_field = str(mapping['mapping_field'])
                        if mapping_field.startswith('mf_'):
                            x.update(
                                {mapping_field[3:]: excel_data_row[excel_columns.index(mapping['template_field'])]})
                        else:
                            x.update(
                                {mapping_field : excel_data_row[excel_columns.index(mapping['template_field'])]})
                    requests.append(x)
        except UnicodeDecodeError as ue:
            file_acceptable = False
            _logger.info(str(ue))
        return requests, file_acceptable

    def send_sps_customer_request_for_processing(self, customer_product_request):
        _logger.info('inside processing %r', customer_product_request.id)
        return None

    @http.route('/userslist', type='http', auth='public', csrf=False)
    def _get_users_list(self, **post):
        # cr, context, pool, uid = request.cr, request.context, request.registry, request.uid
        input_data = post['input_data']
        records = request.env['res.partner'].sudo().search([[input_data, '=', True]])
        response_data = [dict(name=record['name'], id=record['id']) for record in records]
        return str(json.dumps(response_data))

    @http.route('/template_import/set_file', methods=['POST'])
    def set_file(self, file, import_id, customer, template_type, jsonp='callback'):
        import_id = int(import_id)

        written = request.env['sps.template.transient'].browse(import_id).write({
            'file': file.read(),
            'file_name': file.filename,
            'file_type': file.content_type,
            # 'customer_id': customer
        })

        return 'window.top.%s(%s)' % (misc.html_escape(jsonp), json.dumps({'result': written}))
