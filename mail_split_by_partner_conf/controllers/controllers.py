# -*- coding: utf-8 -*-
from odoo import http

# class MailSplitByPartnerConf(http.Controller):
#     @http.route('/mail_split_by_partner_conf/mail_split_by_partner_conf/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mail_split_by_partner_conf/mail_split_by_partner_conf/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('mail_split_by_partner_conf.listing', {
#             'root': '/mail_split_by_partner_conf/mail_split_by_partner_conf',
#             'objects': http.request.env['mail_split_by_partner_conf.mail_split_by_partner_conf'].search([]),
#         })

#     @http.route('/mail_split_by_partner_conf/mail_split_by_partner_conf/objects/<model("mail_split_by_partner_conf.mail_split_by_partner_conf"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mail_split_by_partner_conf.object', {
#             'object': obj
#         })