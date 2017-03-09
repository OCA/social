# -*- coding: utf-8 -*-
# Copyright 2017 Specialty Medical Drugstore, LLC.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from openerp import api, models


class MailChannel(models.Model):

    _inherit = 'mail.channel'

    @api.multi
    def channel_info(self, extra_info=False):
        channel_infos = super(MailChannel, self).channel_info(extra_info)
        partner_mod = self.env['res.partner']
        operator_id = self.env.context.get('im_livechat_operator_partner_id')

        for channel_info in channel_infos:
            if operator_id and channel_info['public'] == 'public':
                operator = partner_mod.browse(operator_id)

                if operator.firstname:
                    operator_name = operator.firstname
                else:
                    operator_name = operator.name

                channel_info['operator_pid'] = \
                    (operator.id, u'%s' % operator_name)

                # channel name format:
                # 'customer name, operator/employee name'
                channel_name = channel_info['name'].split(', ')

                new_channel_name = '%s, %s' % \
                    (channel_name[0], operator_name)

                channel_info['name'] = new_channel_name

        return channel_infos
