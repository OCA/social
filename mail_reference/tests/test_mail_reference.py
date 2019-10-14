# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.tests import common
from odoo.exceptions import ValidationError
from odoo import SUPERUSER_ID


class TestMailReference(common.HttpCase):

    post_install = True
    at_install = False

    def test_mail_reference(self):
        """ This is the testing routine:
        1) Create a valid delimiter ^
        2) Make sure that we cannot create other delimiter records with the
        same symbol
        3) For the valid delimiter ^ we have created, test that when the
        delimiter is used, it is properly resolved.
        """
        model_mention = self.env['mail.reference.mention']
        model_partner = self.env.ref('base.model_res_partner')
        model_company = self.env.ref('base.model_res_company')
        test_company = self.env['res.company'].create({'name': 'test_com'})
        # check that we cannot create a mention with an invalid char
        with self.assertRaises(ValidationError):
            model_mention.create({'delimiter': '#'})
        # create a delimiter on modelA and then create the same delimiter on
        # the same model, verify that you cannot do this
        delimiter = model_mention.create({
            'delimiter': 'b',
            'shows_model_id': model_company.id,
            'shown_at_model_ids': [
                (6, False, (model_partner + model_company).ids)],
        })
        # check name_get's functionality
        self.assertEquals(
            delimiter.name_get()[0][1],
            'Delimiter: %s, Shown At: %s Shows: %s' % (
                delimiter.delimiter,
                ', '.join(delimiter.shown_at_model_ids.mapped('name')),
                delimiter.shows_model_id.name,
            )
        )
        with self.assertRaises(ValidationError):
            model_mention.create({
                'delimiter': 'b',
                'shown_at_model_ids': [(6, False, model_partner.ids)],
            })
        # now use the delimiter created above to see if it is shown correctly
        # and points to the right record.
        self.phantom_js(
            "/",
            "odoo.__DEBUG__.services['mail_reference.tour'].run('reference')",
            "odoo.__DEBUG__.services["
            "'mail_reference.tour'].tours.reference.ready",
            login='admin',
        )
        # now check the message posted on the administrator's form contains
        # the link to the record
        message_body = self.env['res.partner'].browse(
            SUPERUSER_ID).message_ids[0].body
        self.assertIn(
            'data-oe-id="{}"'.format(test_company.id),
            message_body,
        )
        self.assertIn(
            'data-oe-model="{}"'.format(test_company._name),
            message_body,
        )
