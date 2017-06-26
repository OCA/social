# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino
#
#    The licence is in the file __openerp__.py
#
##############################################################################

from openerp import api, models, fields, _
from openerp.exceptions import Warning as UserError
from openerp.tools.safe_eval import safe_eval


class MassMailing(models.Model):
    """ Add a direct link to an e-mail template in order to retrieve all
    Sendgrid configuration into the e-mails. Add ability to force a
    template language.
    """
    _inherit = 'mail.mass_mailing'

    email_template_id = fields.Many2one(
        'mail.template', 'Sengdrid Template',
    )
    lang = fields.Many2one(
        comodel_name="res.lang", string="Force language")
    body_sendgrid = fields.Html(compute='_compute_sendgrid_view')
    # Trick to save html when taken from the e-mail template
    html_copy = fields.Html(
        compute='_compute_sendgrid_view', inverse='_inverse_html_copy')
    enable_unsubscribe = fields.Boolean()
    unsubscribe_text = fields.Char(
        default='If you would like to unsubscribe and stop receiving these '
                'emails <% clickhere %>.')
    unsubscribe_tag = fields.Char()

    @api.depends('body_html')
    def _compute_sendgrid_view(self):
        for wizard in self:
            template = wizard.email_template_id.with_context(
                lang=self.lang.code or self.env.context['lang'])
            sendgrid_template = template.sendgrid_localized_template
            if sendgrid_template and wizard.body_html:
                res_id = self.env[wizard.mailing_model].search(safe_eval(
                    wizard.mailing_domain), limit=1).id
                if res_id:
                    body = template.render_template(
                        wizard.body_html, template.model, [res_id],
                        post_process=True)[res_id]
                    wizard.body_sendgrid = \
                        sendgrid_template.html_content.replace('<%body%>',
                                                               body)
            else:
                wizard.body_sendgrid = wizard.body_html
            wizard.html_copy = wizard.body_html

    def _inverse_html_copy(self):
        for wizard in self:
            wizard.body_html = wizard.html_copy

    @api.onchange('email_template_id')
    def onchange_email_template_id(self):
        if self.email_template_id:
            template = self.email_template_id.with_context(
                lang=self.lang.code or self.env.context['lang'])
            if template.email_from:
                self.email_from = template.email_from
            self.name = template.subject
            self.body_html = template.body_html

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
            self.onchange_email_template_id()

    @api.multi
    def action_test_mailing(self):
        wizard = self
        if self.email_template_id:
            wizard = self.with_context(
                lang=self.lang.code or self.env.context['lang'])
        return super(MassMailing, wizard).action_test_mailing()

    @api.multi
    def send_mail(self):
        self.ensure_one()
        if self.email_template_id:
            # use E-mail Template
            res_ids = self.get_recipients(self)
            if not res_ids:
                raise UserError(_('Please select recipients.'))
            template = self.email_template_id
            composer_values = {
                'template_id': template.id,
                'composition_mode': 'mass_mail',
                'model': template.model,
                'author_id': self.env.user.partner_id.id,
                'res_id': res_ids[0],
                'attachment_ids': [(4, attachment.id) for attachment in
                                   self.attachment_ids],
                'email_from': self.email_from,
                'body': self.body_html,
                'subject': self.name,
                'record_name': False,
                'mass_mailing_id': self.id,
                'mailing_list_ids': [(4, l.id) for l in
                                     self.contact_list_ids],
                'no_auto_thread': self.reply_to_mode != 'thread',
            }
            if self.reply_to_mode == 'email':
                composer_values['reply_to'] = self.reply_to
            composer = self.env['mail.compose.message'].with_context(
                lang=self.lang.code or self.env.context.get('lang', 'en_US'),
                active_ids=res_ids)
            emails = composer.mass_mailing_sendgrid(res_ids, composer_values)
            self.write({
                'state': 'done',
                'sent_date': fields.Datetime.now(),
            })
            return emails
        else:
            # Traditional sending
            return super(MassMailing, self).send_mail()
