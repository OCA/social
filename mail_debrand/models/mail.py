# -*- coding: utf-8 -*-
# © 2016 Antiun Ingeniería S.L. - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import _, api, models, tools


class MailNotification(models.Model):
    _inherit = "mail.notification"

    @api.model
    def get_signature_footer(self, user_id, res_model=None, res_id=None,
                             user_signature=True):
        """Generate signature footer only with the chosen parts.

        Now, you can set ``skip_signature_user=True`` in the context to remove
        the user signature (it's the same as ``user_signature=False``), and
        ``skip_signature_company=True`` to remove the company's.
        """
        user = self.env["res.users"].browse(user_id)
        parts = list()

        if user_signature and not self.env.context.get("skip_signature_user"):
            parts.append(self._get_signature_footer_user(user))

        if not self.env.context.get("skip_signature_company"):
            parts.append(self._get_signature_footer_company(user))

        footer = ""
        for part in parts:
            footer = tools.append_content_to_html(
                footer, part, plaintext=False)

        return footer

    @api.model
    def _get_signature_footer_user(self, user):
        """User part of the signature."""
        return user.signature if user.signature else "--<br />%s" % user.name

    def _get_signature_footer_company(self, user):
        """Company part of the signature."""
        website = user.company_id.website
        if website:
            if not website.startswith(('http:', 'https:')):
                website = "http://" + website
            company = ("<a href='%s'>%s</a>" %
                       (website, user.company_id.name))
        else:
            company = user.company_id.name
        return _('Sent by %s') % company
