# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestAttachExistingAttachment(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner_02 = self.env.ref('base.res_partner_address_17')
        self.default_model = 'res.partner'
        self.default_res_id = self.env.ref('base.res_partner_10').id

    def test_send_email_attachment(self):
        ctx = self.env.context.copy()
        ctx.update({
            'default_model': self.default_model,
            'default_res_id': self.default_res_id,
            'default_composition_mode': 'comment',
        })
        mail_compose = self.env['mail.compose.message']
        values = mail_compose.with_context(ctx)\
            .onchange_template_id(False, 'comment', self.default_model,
                                  self.default_res_id)['value']
        values['partner_ids'] = [(4, self.partner_02.id)]
        compose_id = mail_compose.with_context(ctx).create(values)
        compose_id.autofollow_recipients = False
        compose_id.with_context(ctx).send_mail()
        res = self.env["mail.followers"].search(
            [('res_model', '=', self.default_model),
             ('res_id', '=', self.default_res_id),
             ('partner_id', '=', self.partner_02.id)])
        # I check if the recipient isn't a follower
        self.assertEqual(len(res.ids), 0)
        res = self.env["mail.followers"].search(
            [('res_model', '=', self.default_model),
             ('res_id', '=', self.default_res_id),
             ('partner_id', '=', self.env.user.partner_id.id)])
        # I check if the current user is a follower
        # (by default with 'mail_create_nosubscribe')
        self.assertEqual(len(res.ids), 1)
        compose_id = mail_compose.with_context(ctx).create(values)
        compose_id.autofollow_recipients = True
        compose_id.with_context(ctx).send_mail()
        res = self.env["mail.followers"].search(
            [('res_model', '=', self.default_model),
             ('res_id', '=', self.default_res_id),
             ('partner_id', '=', self.partner_02.id)])
        # I check if the recipient is a follower
        self.assertEqual(len(res.ids), 1)

    def test_send_invoice(self):
        self.default_model = 'account.invoice'
        self.default_res_id = self.env.ref(
            'l10n_generic_coa.demo_invoice_3').id
        self.test_send_email_attachment()
