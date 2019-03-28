# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.main import MailController as _MailController


class MailController(_MailController):
    @http.route()
    def read_subscription_data(self, res_model, follower_id):
        """Add custom notification data to subscriptions"""
        subtypes_list = super(MailController, self).read_subscription_data(
            res_model, follower_id,
        )
        follower = request.env['mail.followers'].browse(follower_id)
        for subtype_dict in subtypes_list:
            subtype = request.env['mail.message.subtype'].browse(
                subtype_dict['id']
            )
            subtype_dict['force_mail'] = 'default'
            if subtype in follower.force_mail_subtype_ids:
                subtype_dict['force_mail'] = 'force_yes'
            elif subtype in follower.force_nomail_subtype_ids:
                subtype_dict['force_mail'] = 'force_no'
            subtype_dict['force_own'] = (
                subtype in follower.force_own_subtype_ids
            )
        return subtypes_list
