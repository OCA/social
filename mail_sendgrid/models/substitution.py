# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Roman Zoller, Emanuel Cino
#
#    The licence is in the file __openerp__.py
#
##############################################################################

from openerp import models, fields


class Substitution(models.Model):
    """ Substitution values for a SendGrid email message """
    _name = 'sendgrid.substitution'

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    key = fields.Char()
    lang = fields.Char()
    email_template_id = fields.Many2one(
        'email.template', ondelete='cascade')
    email_id = fields.Many2one(
        'mail.mail', ondelete='cascade')
    value = fields.Char()
