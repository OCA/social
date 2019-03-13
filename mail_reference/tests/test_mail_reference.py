# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from openerp.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestMailReference(TransactionCase):

    post_install = True
    at_install = False

    def test_mail_reference(self):
        model_mention = self.env['mail.reference.mention']
        model_model = self.env['ir.model']
        model_partner = model_model.search([('model', '=', 'res.partner')])
        model_company = model_model.search([('model', '=', 'res.company')])
        # check that we cannot create a mention with an invalid char
        with self.assertRaises(ValidationError):
            model_mention.create({'delimiter': '#'})
        # create a delimiter on modelA and then create the same delimiter on
        # the same model, verify that you cannot do this
        model_mention.create({
            'delimiter': '$',
            'shown_at_model_ids': [
                (6, False, (model_partner + model_company).ids)],
        })
        with self.assertRaises(ValidationError):
            model_mention.create({
                'delimiter': '$',
                'shown_at_model_ids': [(6, False, model_partner.ids)],
            })
        # now create a proper delimiter and verify that it is shown correctly
