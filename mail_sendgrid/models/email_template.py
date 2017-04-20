# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Roman Zoller
#
#    The licence is in the file __openerp__.py
#
##############################################################################

from openerp import models, fields, api


class EmailTemplate(models.Model):
    _inherit = 'mail.template'

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    substitution_ids = fields.One2many(
        'sendgrid.substitution', 'email_template_id', 'Substitutions')
    sendgrid_template_ids = fields.One2many(
        'sendgrid.email.lang.template', 'email_template_id',
        'Sendgrid Templates')
    sendgrid_localized_template = fields.Many2one(
        'sendgrid.template', compute='_compute_localized_template')

    def _compute_localized_template(self):
        lang = self.env.context.get('lang', 'en_US')
        for template in self:
            lang_template = template.sendgrid_template_ids.filtered(
                lambda t: t.lang == lang)
            if lang_template and len(lang_template) == 1:
                template.sendgrid_localized_template = \
                    lang_template.sendgrid_template_id

    @api.multi
    def update_substitutions(self):
        self.ensure_one()
        new_substitutions = list()
        for language_template in self.sendgrid_template_ids:
            sendgrid_template = language_template.sendgrid_template_id
            lang = language_template.lang
            substitutions = self.substitution_ids.filtered(
                lambda s: s.lang == lang)
            keywords = sendgrid_template.get_keywords()
            # Add new keywords from the sendgrid template
            for key in keywords:
                if key not in substitutions.mapped('key'):
                    substitution_vals = {
                        'key': key,
                        'lang': lang,
                        'email_template_id': self.id
                    }
                    new_substitutions.append((0, 0, substitution_vals))

        return self.write({'substitution_ids': new_substitutions})

    @api.multi
    def render_substitutions(self, res_ids):
        """
        :param res_ids: resource ids for rendering the template
        Returns values for substitutions in a mail.message creation
        :return:
            Values for mail creation (for each resource id given)
         {res_id: list of substitutions values [0, 0 {substitution_vals}]}
        """
        self.ensure_one()
        if isinstance(res_ids, (int, long)):
            res_ids = [res_ids]
        substitutions = self.substitution_ids.filtered(
            lambda s: s.lang == self.env.context.get('lang', 'en_US'))
        substitution_vals = {res_id: list() for res_id in res_ids}
        for substitution in substitutions:
            values = self.render_template(
                substitution.value, self.model, res_ids)
            for res_id in res_ids:
                substitution_vals[res_id].append((0, 0, {
                    'key': substitution.key,
                    'value': values[res_id]
                }))
        return substitution_vals
