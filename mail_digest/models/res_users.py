# -*- coding: utf-8 -*-
# Copyright 2017 Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights.

        Access rights are disabled by default, but allowed
        on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.

        [copied from mail.models.users]
        """
        super(Users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(['notify_frequency'])
        type(self).SELF_WRITEABLE_FIELDS.extend(['notify_conf_ids'])
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        type(self).SELF_READABLE_FIELDS.extend(['notify_frequency'])
        type(self).SELF_READABLE_FIELDS.extend(['notify_conf_ids'])
