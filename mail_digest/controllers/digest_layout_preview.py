# -*- coding: utf-8 -*-
# Copyright 2018 Simone Orsi <simone.orsi@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request
import random


FAKE_NAMES = [
    'Madison Castillo',
    'Destiny Frost',
    'Dennis Parrish',
    'Christy Moore',
    'Larry James',
    'David Simmons',
    'Dr. Francis Ramos',
    'Michelle Williams',
    'Allison Montgomery',
    'Michelle Rodriguez',
    'Gina Patel',
    'Corey Ray',
    'Brent Myers',
    'Sydney Hicks',
    'Austin Buckley',
    'Patricia Jones DDS',
    'Dylan Davila',
    'Christopher Bolton',
    'James Cline',
    'Gary Johnson',
    'Jennifer Reese',
    'Kevin Davis',
    'Sandra Robinson',
    'Sara Warner',
    'Jaime Dunn',
    'Mark Austin',
    'Kendra Nelson',
    'Matthew White',
    'Rebecca Berger',
    'Amanda Thornton',
    'Lorraine Schultz',
    'Chelsea Daniel',
    'Kayla Jackson',
    'Melanie Grant',
    'Oscar Jones',
    'Jon Sanchez',
    'Kevin Anderson',
    'Yvonne Mullen',
    'Jonathan King',
    'Wendy Hernandez'
]

FAKE_NUMBERS = range(1, 30)


class DigestPreview(http.Controller):

    digest_test_template = 'mail_digest.digest_layout_preview'

    @http.route([
        '/digest/layout-preview',
    ], type='http', auth='user')
    def digest_test(self):
        digest = self._fake_digest()
        mail_values = digest._get_email_values()
        values = {
            'env': request.env,
            'digest_html': mail_values['body_html'],
        }
        return request.render(self.digest_test_template, values)

    def _fake_digest(self):
        user = request.env.user
        digest_model = request.env['mail.digest'].sudo()
        digest = digest_model.new()
        digest.partner_id = user.partner_id
        digest.digest_template_id = digest._default_digest_template_id()
        digest.message_ids = self._fake_messages()
        digest.sanitize_msg_body = True
        return digest

    def _fake_messages(self):
        messages = request.env['mail.message'].sudo()
        subtype_model = request.env['mail.message.subtype'].sudo()
        subtypes = subtype_model.search([])
        records = request.env['res.partner'].sudo().search([])
        # TODO: filter subtypes?
        for i, subtype in enumerate(subtypes):
            # generate a couple of messages for each type
            for x in range(1, 3):
                msg = messages.new()
                msg.subtype_id = subtype
                subject, body = self._fake_content(subtype, i, x)
                msg.subject = subject
                msg.message_type = random.choice(
                    ('email', 'comment', 'notification'))
                msg.email_from = 'random@user%d.com' % i
                msg.partner_ids = [(6, 0, request.env.user.partner_id.ids)]
                if i + x % 2 == 0:
                    # relate a document
                    msg.model = records._name
                    msg.res_id = random.choice(records.ids)
                # simulate messages w/ no body but tracking values
                if x == random.choice([1, 2]):
                    msg.tracking_value_ids = self._fake_tracking_vals()
                else:
                    msg.body = body
                messages += msg
        return messages

    def _fake_content(self, subtype, i, x):
        subject = 'Lorem ipsum %d / %d' % (i, x)
        body = 'Random text here lorem ipsum %d / %d' % (i, x)
        if i % 2 == 0 and x > 1:
            # simulate also random styles that are goin to be stripped
            body = """
            <p style="font-size: 13px; font-family: &quot;Lucida Grande&quot;, Helvetica, Verdana, Arial, sans-serif; margin: 0px 0px 9px 0px">Lorem ipsum dolor sit amet, cetero menandri mel id.</p>

            <p>Ad modus tantas qui, quo choro facete delicata te.
            Epicurei accusata vix eu, prima erant graeci sit te,
            vivendum molestiae an mel.</p>

            <p>Sed apeirian atomorum id, no ius possit antiopam molestiae.</p>
            """  # noqa
        return subject, body.strip()

    def _fake_tracking_vals(self):
        tracking_model = request.env['mail.tracking.value'].sudo()
        track_vals1 = tracking_model.create_tracking_values(
            random.choice(FAKE_NAMES), random.choice(FAKE_NAMES),
            'name', {'type': 'char', 'string': 'Name'},
        )
        track_vals2 = tracking_model.create_tracking_values(
            random.choice(FAKE_NUMBERS), random.choice(FAKE_NUMBERS),
            'count', {'type': 'integer', 'string': 'Count'},
        )
        return [
            (0, 0, track_vals1),
            (0, 0, track_vals2),
        ]
