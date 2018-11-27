# Copyright 2018 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, fields
from odoo.exceptions import MissingError
from uuid import uuid4
from base64 import urlsafe_b64encode, urlsafe_b64decode
import binascii
import lxml
from werkzeug.urls import url_parse
from datetime import date
from dateutil.relativedelta import relativedelta


class Mail(models.Model):
    _inherit = 'mail.mail'

    access_token = fields.Char(
        'Security Token',
        compute="_compute_access_token",
        store=True, readonly=True
    )
    view_in_browser_url = fields.Char(
        'View URL',
        compute="_compute_browser_url"
    )
    is_token_alive = fields.Boolean(
        "Is Token alive",
        compute="_compute_token_alive"
    )

    @api.model
    def create(self, vals):
        rec = super(Mail, self).create(vals)
        rec._replace_view_url()
        return rec

    @api.model
    def get_record_for_token(self, token):
        """Parse the URL token to get the matching record.

        The token is a base 64 encoded string containing:
            * 32 positions access token
            * Record ID
        Returns a record matching the token or empty recordset if not found
        """
        try:
            token = urlsafe_b64decode(token).decode()
            access_token, rec_id = token[:32], token[32:]
            rec = self.sudo().search([
                ('id', '=', int(rec_id)),
                ('access_token', '=', access_token)
            ])
            res = rec.is_token_alive and rec
        except (ValueError, MissingError, binascii.Error):
            res = False
        finally:
            return res or self.browse()

    @api.multi
    def _get_full_url(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        base = url_parse(base_url)

        return url_parse(
            self.view_in_browser_url or '#'
        ).replace(
            scheme=base.scheme, netloc=base.netloc
        ).to_url()

    @api.multi
    def _replace_view_url(self):
        """Replace placeholders with record URL.

        Replace the 'href' attribute of all `<a></a>` tags
        having the 'class' attribute equal to 'view_in_browser_url'
        with the URL generated for this mail.mail record
        inside the rendered 'body_html' from the template.
        In case the value `auto_delete` for the record is `True`,
        the placeholders will be removed.
        """
        self.ensure_one()

        root_html = lxml.html.fromstring(self.body_html)
        link_nodes = root_html.xpath("//a[hasclass('view_in_browser_url')]")

        if link_nodes:
            if self.auto_delete:
                for node in link_nodes:
                    node.drop_tree()
            else:
                full_url = self._get_full_url()
                for node in link_nodes:
                    node.set('href', full_url)

            self.body_html = lxml.html.tostring(
                root_html,
                pretty_print=False,
                method='html',
                encoding='unicode'
            )

    @api.depends('create_date')
    def _compute_access_token(self):
        for rec in self:
            rec.access_token = uuid4().hex

    @api.depends('access_token')
    def _compute_browser_url(self):
        for rec in self:
            url_token = urlsafe_b64encode(
                (rec.access_token + str(rec.id)).encode()
            ).decode()
            rec.view_in_browser_url = '/email/view/{}'.format(url_token)

    @api.depends('mail_message_id',
                 'mail_message_id.date')
    def _compute_token_alive(self):
        expiration_time = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'mail_browser_view.token_expiration_hours'
            ) or '0'
        )
        if expiration_time > 0:
            max_delta = relativedelta(hours=expiration_time)
            for rec in self:
                mail_date = fields.Datetime.from_string(
                    rec.mail_message_id.date
                )
                rec.is_token_alive = (
                    (mail_date + max_delta).date() >= date.today()
                )
        else:
            self.update({'is_token_alive': True})
