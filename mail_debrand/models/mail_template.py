# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
from odoo import _, api, models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.multi
    def generate_email(self, res_ids, fields=None):
        mail_template = self.env.ref(
            'mail.mail_template_data_notification_email_default'
        )
        if self == mail_template:
            obj = self.with_context(mail_debrand=True)
        else:
            obj = self
        return super(MailTemplate, obj).generate_email(res_ids, fields=fields)

    @api.model
    def _debrand_body(self, body):
        using_word = _('using')
        odoo_word = _('Odoo')
        return re.sub(
            using_word + "(.*)[\r\n]*(.*)>" + odoo_word + r"</a>", "", body,
        )

    @api.model
    def render_template(self, template_txt, model, res_ids,
                        post_process=False):
        res = super(MailTemplate, self).render_template(
            template_txt, model, res_ids, post_process=post_process,
        )
        if post_process and self.env.context.get('mail_debrand'):
            if isinstance(res, str):
                res = self._debrand_body(res)
            else:
                for res_id, body in res.items():
                    res[res_id] = self._debrand_body(body)
        return res
