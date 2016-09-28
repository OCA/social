# -*- coding: utf-8 -*-
################################################################
#    License, author and contributors information in:          #
#    __openerp__.py file at the root folder of this module.    #
################################################################

import base64
import copy
import datetime
import dateutil.relativedelta as relativedelta
import logging
import lxml
import urlparse
import openerp
from urllib import urlencode, quote as quote

from openerp import _, api, fields, models, SUPERUSER_ID
from openerp import tools
from openerp import report as odoo_report
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    email_bcc = fields.Char(string='Bcc',
                            help='Blind carbon copy message recipients')

    @api.multi
    def generate_email(self, res_ids, fields=None):
        """Generates an email from the template for given the given model based on
        records given by res_ids.

        :param template_id: id of the template to render.
        :param res_id: id of the record to use for rendering the template (model
                       is taken from template definition)
        :returns: a dict containing all relevant fields for creating a new
                  mail.mail entry, with one extra key ``attachments``, in the
                  format [(report_name, data)] where data is base64 encoded.
        """
        self.ensure_one()
        multi_mode = True
        if isinstance(res_ids, (int, long)):
            res_ids = [res_ids]
            multi_mode = False
        if fields is None:
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to']
	fields = fields + ['email_bcc']

        res_ids_to_templates = self.get_email_template_batch(res_ids)

        # templates: res_id -> template; template -> res_ids
        templates_to_res_ids = {}
        for res_id, template in res_ids_to_templates.iteritems():
            templates_to_res_ids.setdefault(template, []).append(res_id)

        results = dict()
        for template, template_res_ids in templates_to_res_ids.iteritems():
            Template = self.env['mail.template']
            # generate fields value for all res_ids linked to the current template
            if template.lang:
                Template = Template.with_context(lang=template._context.get('lang'))
            for field in fields:
                Template = Template.with_context(safe=field in {'subject'})
                generated_field_values = Template.render_template(
                    getattr(template, field), template.model, template_res_ids,
                    post_process=(field == 'body_html'))
                for res_id, field_value in generated_field_values.iteritems():
	                results.setdefault(res_id, dict())[field] = field_value
            # compute recipients
            if any(field in fields for field in ['email_to', 'partner_to', 'email_cc']):
                results = template.generate_recipients(results, template_res_ids)
            # update values for all res_ids
            for res_id in template_res_ids:
                values = results[res_id]
                # body: add user signature, sanitize
                if 'body_html' in fields and template.user_signature:
                    signature = self.env.user.signature
                    if signature:
                        values['body_html'] = tools.append_content_to_html(values['body_html'], signature, plaintext=False)
                if values.get('body_html'):
                    values['body'] = tools.html_sanitize(values['body_html'])
                # technical settings
                values.update(
                    mail_server_id=template.mail_server_id.id or False,
                    auto_delete=template.auto_delete,
                    model=template.model,
                    res_id=res_id or False,
                    attachment_ids=[attach.id for attach in template.attachment_ids],
                )

            # Add report in attachments: generate once for all template_res_ids
            if template.report_template and not 'report_template_in_attachment' in self.env.context:
                for res_id in template_res_ids:
                    attachments = []
                    report_name = self.render_template(template.report_name, template.model, res_id)
                    report = template.report_template
                    report_service = report.report_name

                    if report.report_type in ['qweb-html', 'qweb-pdf']:
                        result, format = self.pool['report'].get_pdf(self._cr, self._uid, [res_id], report_service, context=Template._context), 'pdf'
                    else:
                        result, format = odoo_report.render_report(self._cr, self._uid, [res_id], report_service, {'model': template.model}, Template._context)

                    # TODO in trunk, change return format to binary to match message_post expected format
                    result = base64.b64encode(result)
                    if not report_name:
                        report_name = 'report.' + report_service
                    ext = "." + format
                    if not report_name.endswith(ext):
                        report_name += ext
                    attachments.append((report_name, result))
                    results[res_id]['attachments'] = attachments

        return multi_mode and results or results[res_ids[0]]


    @api.multi
    def generate_recipients(self, results, res_ids):
        """Generates the recipients of the template. Default values can ben generated
        instead of the template values if requested by template or context.
        Emails (email_to, email_cc) can be transformed into partners if requested
        in the context. """
        self.ensure_one()

        if self.use_default_to or self._context.get('tpl_force_default_to'):
            default_recipients = self.env['mail.thread'].message_get_default_recipients(res_model=self.model, res_ids=res_ids)
            for res_id, recipients in default_recipients.iteritems():
                results[res_id].pop('partner_to', None)
                results[res_id].update(recipients)

        for res_id, values in results.iteritems():
            partner_ids = values.get('partner_ids', list())
            if self._context.get('tpl_partners_only'):
                mails = tools.email_split(values.pop('email_to', '')) + tools.email_split(values.pop('email_cc', '')) + tools.email_split(values.pop('email_bcc', ''))
                for mail in mails:
                    partner_id = self.env['res.partner'].find_or_create(mail)
                    partner_ids.append(partner_id)
            partner_to = values.pop('partner_to', '')
            if partner_to:
                # placeholders could generate '', 3, 2 due to some empty field values
                tpl_partner_ids = [int(pid) for pid in partner_to.split(',') if pid]
                partner_ids += self.env['res.partner'].sudo().browse(tpl_partner_ids).exists().ids
            results[res_id]['partner_ids'] = partner_ids
        return results

