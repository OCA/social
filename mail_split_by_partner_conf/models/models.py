# -*- coding: utf-8 -*-

from odoo import models, fields, api

# class mail_split_by_partner_conf(models.Model):
#     _name = 'mail_split_by_partner_conf.mail_split_by_partner_conf'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100