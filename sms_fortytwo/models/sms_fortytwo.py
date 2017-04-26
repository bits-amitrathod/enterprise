# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import re
import requests

from odoo import fields, models

_logger = logging.getLogger(__name__)


FORTYTWO_URL_ENDPOINT = 'https://rest.fortytwo.com'


class FortyTwoProvider(models.Model):
    _inherit = 'sms.provider'

    provider = fields.Selection(selection_add=[('fortytwo', 'FortyTwo')])
    fortytwo_access_key = fields.Char('FortyTwo SMS Token', groups="base.group_system", help="Token required to send SMS text messages. Get it from the fortytwo interface on https://controlpanel.fortytwo.com/")

    # -------------------------------------------------------------------
    # Method to define from sms.provider, with correct naming convention.
    # -------------------------------------------------------------------
    def _fortytwo_send_sms(self, message, mobile_numbers):
        """ Prepare the request to send to FortyTwo server.
            :param message: plaintext message to send by sms
            :param mobile_numbers: list of strings containing the (unformatted) mobile numbers

            A FortyTwo Request is as following (format is described at https://www.fortytwo.com/apis/sms-gateway-rest-api/request-body/) :
                {
                    "destinations": [
                        {
                            "number": "35676000000",
                            "custom_id": "ce0003"
                        },
                        {
                            "number": "35676000001",
                            "custom_id": "ce0004"
                        }
                    ],
                    "sms_content": {
                        "message": "This is a real test message to say hello. This now is also a much longer message that will span over multiple pages if long enough. I will keep typing until I exceed the 160 character mark. OK done. End of message.",
                        "encoding": "GSM7",
                        "sender_id": "MyCompany"
                    },
                    "callback_url": "http://192.168.11.31/sms_callback.php",  # we decided to not handle callbacks
                    "ttl": 600,  # seconds for which Fortytwo will attemps to send the message
                    "job_id": "job1124"
                }
            And the corresponding response looks like (format is described at https://www.fortytwo.com/apis/sms-gateway-rest-api/response/)
                {
                    "api_job_id": "56af1583-18e9-4753-a3d3-8010699d7a59",
                    "client_job_id": "b0c7801e-0542-4776-8648-cc9f531761f3",
                    "results": {
                        "35676000000": {
                            "message_id": "14480365533520013403",
                            "custom_id": "test12238"
                        },
                        "35676000001": {
                            "message_id": "14480365533540023403",
                            "custom_id": "test12234"
                        }
                    }
                    "result_info": {
                        "status_code": 200,
                        "description": "All Ok."
                    }
                }
            A failed response will contain an empty 'results' dict, and 'status_code' will be the code of the eror (e.g.: 401, ...)
        """
        def _sanitize_mobile_numbers(numbers):
            """ FortyTwo expects a number to be:
                - a String
                - Only digits
                - First digit cannot be a 0
                - Between 7-15 digits long
                - In international format (not verified)
            """
            sanitized_numbers = set()
            for number in numbers:
                number = re.sub("[^0-9]", "", number).lstrip('0')
                if len(number) > 6 and len(number) < 16:
                    sanitized_numbers.add(number)
            return sanitized_numbers

        destinations_data = []
        for number in _sanitize_mobile_numbers(mobile_numbers):
            destinations_data.append({
                'number': number,
            })

        request_payload = {
            "destinations": destinations_data,
            "sms_content": {
                "message": message.encode('utf8'),
                "encoding": "GSM7",
            },
            "ttl": 600,
        }
        headers = {
            "Authorization": 'Token %s' % (self.sudo().fortytwo_access_key,),
            "Content-type": "application/json; charset=utf-8"
        }
        url = FORTYTWO_URL_ENDPOINT + '/1/sms'
        response = requests.post(url, data=json.dumps(request_payload), headers=headers, timeout=5)
        result = response.json()

        status_code = result.get("result_info", {}).get("status_code", "xxx")
        status_description = result.get("result_info", {}).get("description", "Unknown error")
        if status_code != 200:  # failed response from API
            _logger.error('FortyTwo Error %s : %s', status_code, status_description)
            return False
        else:  # success
            return True
