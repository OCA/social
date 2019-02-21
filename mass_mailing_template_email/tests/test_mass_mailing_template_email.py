# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from lxml.etree import fromstring
from openerp.tests.common import HttpCase


class TestMassMailingTemplateEmail(HttpCase):

    post_install = True
    at_install = False

    def test_mass_mailing_template_email(self):
        """
        Our process here is the following:
        1)  Create a mail.mass_mailing record. Verify that no templates are
            shown (the default should be shown but we remove it)
        2)  Create a template with the the model mail.mass_mailing and
            another one with mail.mail, verify that the first
            one is only shown on the mail.mass_mailing record.
        3)  Change the template with the model mail.mail to have
            mail.mass_mailing. See if it is shown on the mass mailing now.
        4)  Delete one template, see if only one is shown on the mass mailing

        NOTE: By default, Odoo looks at the children of
        div['email_designer_themes'] at the `email_designer_snippets` template
        This is how we add templates as well and this is what we are going to
        test, first we find that view, and then check its children.
        """
        def _get_themes():
            snippets = self.env.ref('mass_mailing.email_designer_snippets')
            snippets = snippets.with_context(load_all_views=True)
            full_view = fromstring(snippets.read_combined()['arch'])
            return [x for x in full_view.xpath(
                "//div[@id='email_designer_themes']")[0]]
        mail_template = self.env['mail.template']
        model_mass_mail = self.env.ref('mass_mailing.model_mail_mass_mailing')
        model_mail_mail = self.env.ref('mail.model_mail_mail')
        # 1)
        self.assertFalse(_get_themes())
        # 2)
        template1 = mail_template.create({
            'name': 'template1',
            'model_id': model_mass_mail.id,
            'subject': 'test1',
            'body_html': '<p>test1</p>',
        })
        template2 = mail_template.create({
            'name': 'template2',
            'model_id': model_mail_mail.id,
            'subject': 'test',
            'body_html': '<p>test2</p>',
        })
        self.assertEquals(len(_get_themes()), 1)
        # 3)
        template2.write({'model_id': model_mass_mail.id})
        self.assertEquals(len(_get_themes()), 2)
        # 4)
        template1.unlink()
        self.assertEquals(len(_get_themes()), 1)
