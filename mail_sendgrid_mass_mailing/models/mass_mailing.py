# -*- coding: utf-8 -*-
# Copyright 2016-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _
from odoo.exceptions import Warning as UserError
from odoo.tools.safe_eval import safe_eval


class MassMailing(models.Model):
    """ Add a direct link to an e-mail template in order to retrieve all
    Sendgrid configuration into the e-mails. Add ability to force a
    template language.
    """
    _inherit = 'mail.mass_mailing'

    email_template_id = fields.Many2one(
        'mail.template', 'Sendgrid Template',
    )
    lang = fields.Many2one(
        comodel_name="res.lang", string="Force language")
    body_sendgrid = fields.Html(compute='_compute_sendgrid_view')
    enable_unsubscribe = fields.Boolean()
    unsubscribe_text = fields.Char(
        default='If you would like to unsubscribe and stop receiving these '
                'emails <% clickhere %>.')
    unsubscribe_tag = fields.Char()

    @api.depends('email_template_id')
    def _compute_sendgrid_view(self):
        for wizard in self:
            template = wizard.email_template_id.with_context(
                lang=wizard.lang.code or self.env.context['lang'])
            sendgrid_template = template.sendgrid_localized_template
            if sendgrid_template:
                res_id = self.env[wizard.mailing_model].search(safe_eval(
                    wizard.mailing_domain), limit=1).id
                if res_id:
                    body = template.render_template(
                        template.body_html, template.model, [res_id],
                        post_process=True)[res_id]
                    wizard.body_sendgrid = \
                        sendgrid_template.html_content.replace('<%body%>',
                                                               body)

    @api.multi
    def write(self, vals):
        # Take settings from mail template
        template_id = vals.get('email_template_id')
        if template_id:
            template = self.env['mail.template'].browse(template_id)
            if template.email_from:
                vals['email_from'] = template.email_from
            if template.reply_to:
                vals['reply_to'] = template.reply_to
            vals['name'] = template.subject
        return super(MassMailing, self).write(vals)

    @api.onchange('lang')
    def onchange_lang(self):
        if self.lang and self.mailing_model == 'res.partner':
            domain = safe_eval(self.mailing_domain)
            lang_tuple = False
            for tuple in domain:
                if tuple[0] == 'lang':
                    lang_tuple = tuple
                    break
            if lang_tuple:
                domain.remove(lang_tuple)
            domain.append(('lang', '=', self.lang.code))
            self.mailing_domain = str(domain)

    @api.multi
    def action_test_mailing(self):
        wizard = self
        if self.email_template_id:
            wizard = self.with_context(
                lang=self.lang.code or self.env.context['lang'])
        return super(MassMailing, wizard).action_test_mailing()

    @api.multi
    def send_mail(self):
        sendgrid = self.filtered('email_template_id')
        emails = self.env['mail.mail']
        for mailing in sendgrid:
            # use E-mail Template
            res_ids = mailing.get_recipients()
            if not res_ids:
                raise UserError(_('Please select recipients.'))
            lang = mailing.lang.code or self.env.context.get('lang', 'en_US')
            mailing = mailing.with_context(lang=lang)
            composer_values = mailing._send_mail_get_composer_values()
            if mailing.reply_to_mode == 'email':
                composer_values['reply_to'] = mailing.reply_to
            composer = self.env['mail.compose.message'].with_context(
                lang=lang, active_ids=res_ids)
            emails += composer.mass_mailing_sendgrid(res_ids, composer_values)
            mailing.write({
                'state': 'done',
                'sent_date': fields.Datetime.now(),
            })
        # Traditional sending
        super(MassMailing, self - sendgrid).send_mail()
        return emails

    def _send_mail_get_composer_values(self):
        """
        Get the values used for the mail.compose.message wizard that will
        generate the e-mails of a mass mailing campaign.
        :return: dictionary of mail.compose.message values
        """
        template = self.email_template_id
        author = self.mass_mailing_campaign_id.user_id.partner_id or \
            self.env.user.partner_id
        return {
            'template_id': template.id,
            'composition_mode': 'mass_mail',
            'model': template.model,
            'author_id': author.id,
            'attachment_ids': [(4, attachment.id) for attachment in
                               self.attachment_ids],
            'email_from': self.email_from,
            'body': template.body_html,
            'subject': self.name,
            'record_name': False,
            'mass_mailing_id': self.id,
            'mailing_list_ids': [(4, l.id) for l in
                                 self.contact_list_ids],
            'no_auto_thread': self.reply_to_mode != 'thread',
        }
