# -*- coding: utf-8 -*-
# Copyright 2015-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class Substitution(models.Model):
    """ Substitution values for a SendGrid email message """
    _name = 'sendgrid.substitution'

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    key = fields.Char()
    lang = fields.Char()
    email_template_id = fields.Many2one(
        'mail.template', ondelete='cascade', index=True)
    email_id = fields.Many2one(
        'mail.mail', ondelete='cascade', index=True)
    value = fields.Char()
