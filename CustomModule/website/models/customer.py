from odoo import api, fields, models


class Customer(models.Model):
    _name = 'customer'

    firstname = fields.Char('abc')
