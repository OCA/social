# Copyright 2025 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import markupsafe

from odoo import api, exceptions, fields, models


class IrServerAction(models.Model):
    _inherit = "ir.actions.server"

    state = fields.Selection(
        selection_add=[("whatsapp", "WhatsApp message")],
        ondelete={"whatsapp": "cascade"},
    )
    whatsapp_gateway_id = fields.Many2one(
        comodel_name="mail.gateway", domain=[("gateway_type", "=", "whatsapp")]
    )
    whatsapp_partner = fields.Char()
    whatsapp_template_id = fields.Many2one(
        comodel_name="mail.whatsapp.template",
        domain="[('gateway_id', '=', whatsapp_gateway_id),('model_id', '=', model_id)]",
    )

    @api.depends("state")
    def _compute_available_model_ids(self):
        gateway_based = self.filtered(lambda action: action.state == "whatsapp")
        if gateway_based:
            mail_models = self.env["ir.model"].search(
                [("is_mail_thread", "=", True), ("transient", "=", False)]
            )
            gateway_based.available_model_ids = mail_models.ids
        return super(
            IrServerAction, self - gateway_based
        )._compute_available_model_ids()

    @api.constrains("state", "model_id")
    def _check_whatsapp_model_coherency(self):
        for action in self:
            if action.state == "whatsapp" and (
                action.model_id.transient or not action.model_id.is_mail_thread
            ):
                raise exceptions.ValidationError(
                    self.env._(
                        "Sending WhatsApp message can only be done on a non transient "
                        "mail.thread model"
                    )
                )

    def _run_action_whatsapp_multi(self, eval_context=None):
        # Method called by upstream in ir.actions~_get_runner() using naming convention
        context = self.env.context
        if (
            not self.whatsapp_template_id
            or (not context.get("active_ids") and not context.get("active_id"))
            or self._is_recompute()
        ):
            return False
        res_ids = context.get("active_ids", [context.get("active_id")])
        for record in self.env[self.model_id.model].browse(res_ids):
            partner_id = int(
                self.env["mail.render.mixin"]._render_template(
                    self.whatsapp_partner, record._name, [record.id]
                )[record.id]
            )
            partner = self.env["res.partner"].browse(partner_id)
            partner._whatsapp_get_channel("mobile", self.whatsapp_gateway_id)
            gateway_channel = partner.gateway_channel_ids.filtered(
                lambda x: x.gateway_id == self.whatsapp_gateway_id
            )
            body = markupsafe.Markup(
                self.whatsapp_template_id.with_context(
                    default_res_id=record.id
                ).render_body_message()
            )
            # pylint: disable=translation-required
            record.with_context(
                whatsapp_template_id=self.whatsapp_template_id.id, res_id=record.id
            ).message_post(
                body=body,
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
                gateway_notifications=[
                    {
                        "channel_type": "gateway",
                        "gateway_channel_id": gateway_channel.id,
                        "partner_id": partner_id,
                    }
                ],
            )
        return False
