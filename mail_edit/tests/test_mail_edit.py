# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.tests.common import TransactionCase


class TestMailEdit(TransactionCase):
    def setUp(self, *args, **kwargs):
        # make sale.order and res_partner allowed to edit
        super(TestMailEdit, self).setUp(*args, **kwargs)
        self.rrl_partner = self.env['res.request.link'].create({
            'name': 'Partner',
            'object': 'res.partner',
            'priority': 1,
            'mail_edit': True,
        })
        self.rrl_partner = self.env['res.request.link'].create({
            'name': 'Partner',
            'object': 'res.partner',
            'priority': 1,
            'mail_edit': True,
        })
        self.sender = self.env['res.partner'].create({
            'name': 'Test sender',
            'email': 'sender@example.com',
            'notify_email': 'always',
        })
        self.recipient = self.env['res.partner'].create({
            'name': 'Test recipient',
            'email': 'recipient@example.com',
            'notify_email': 'always',
        })
        self.product = self.env['product.product'].create({
            'name':  'product_test',
            'type': 'product',
            'uos_id': self.env.ref('product.product_uom_categ_unit').id,
        })

    def test_mail_edit(self):
        # This message will generate a notification for recipient
        message = self.env['mail.message'].create({
            'subject': 'Message test',
            'author_id': self.sender.id,
            'email_from': self.sender.email,
            'message_type': 'comment',
            'model': 'res.partner',
            'res_id': self.recipient.id,
            'partner_ids': [(4, self.recipient.id)],
            'body': '<p>This is a test message</p>',
        })
        # verify model selection present
        model_selection = message._get_model_selection()
        models = zip(*model_selection)[0].ids
        self.assertTrue(self.rrl_sale.id and self.rrl_partner.id in models)
        # move the message from partner to sale
        message.write({'destination_object_id': self.product.id})
        self.assertEqual(
            message.record_name,
            "%s %s" % (
                self.env["ir.model"].search([(
                    "model", '=', message.destination_object_id._name)]).name,
                message.destination_object_id.display_name
            )
        )
