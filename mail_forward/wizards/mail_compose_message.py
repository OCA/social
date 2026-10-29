# Copyright 2024 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    forward_type = fields.Selection(
        [
            ("current_thread", "Current thread"),
            ("another_thread", "Another thread"),
        ],
        default="current_thread",
    )
    forward_thread = fields.Reference(
        selection="_selection_forward_thread", string="Thread to forward"
    )

    @api.model
    def _selection_forward_thread(self):
        # Get all models available to be selected by the user.
        # Only consider models that support posted messages and are not transient.
        models = (
            self.env["ir.model"]
            .sudo()
            .search(
                [
                    ("transient", "=", False),
                    ("is_mail_thread", "=", True),
                    ("enable_forward_to", "=", True),
                ],
                order="name asc",
            )
        )
        selection_values = []
        for model in models:
            if (
                model.model in self.env and self.env[model.model]._auto
            ):  # No Abstract models or reports
                selection_values.append((model.model, model.name))
        return selection_values

    @api.depends(
        "composition_mode",
        "model",
        "res_domain",
        "res_ids",
        "template_id",
        "forward_type",
    )
    @api.depends_context("message_forwarded_id")
    def _compute_attachment_ids(self):
        # Save the attachments before calling super() to avoid losing them
        # because when template_id is not set,
        # attachment_ids is set to False in the super() call.
        old_attachments = {composer.id: composer.attachment_ids for composer in self}
        res = super()._compute_attachment_ids()
        if self.env.context.get("message_forwarded_id"):
            # Add the attachments from the original message.
            message_forwarded = self.env["mail.message"].browse(
                self.env.context["message_forwarded_id"]
            )
            for composer in self:
                composer.attachment_ids |= old_attachments[composer.id]
                for attachment in message_forwarded.attachment_ids:
                    composer.attachment_ids |= attachment
        return res

    @api.depends(
        "composition_mode",
        "model",
        "res_domain",
        "res_ids",
        "template_id",
        "forward_type",
        "forward_thread",
    )
    @api.depends_context("message_forwarded_id")
    def _compute_body(self):
        res = super()._compute_body()
        if self.env.context.get("message_forwarded_id"):
            # Set the body by default, taking it from the original message.
            message_forwarded = self.env["mail.message"].browse(
                self.env.context["message_forwarded_id"]
            )
            for composer in self.filtered(lambda c: not c.body):
                composer.body = message_forwarded._build_message_body_for_forward()
        return res

    @api.depends(
        "composition_mode",
        "model",
        "parent_id",
        "record_name",
        "res_domain",
        "res_ids",
        "template_id",
        "forward_type",
        "forward_thread",
    )
    @api.depends_context("message_forwarded_id")
    def _compute_subject(self):
        res = super()._compute_subject()
        if self.env.context.get("message_forwarded_id"):
            # Set the subject by default,
            # because when change the model and res_ids,
            # the subject is taken from the new record.
            message_forwarded = self.env["mail.message"].browse(
                self.env.context["message_forwarded_id"]
            )
            for composer in self:
                composer.subject = f"{_('Fwd:')} {message_forwarded.subject}"
        return res

    @api.depends("composition_mode", "parent_id", "forward_type", "forward_thread")
    @api.depends_context("message_forwarded_id")
    def _compute_model(self):
        res = super()._compute_model()
        if self.env.context.get("message_forwarded_id"):
            # Set the model to the record to be forwarded
            # if the composer is set to forward a record
            # it sends the message to the record to be forwarded
            for composer in self.filtered(
                lambda c: c.forward_type == "another_thread" and c.forward_thread
            ):
                composer.model = composer.forward_thread._name
        return res

    @api.depends("composition_mode", "parent_id", "forward_type", "forward_thread")
    @api.depends_context("message_forwarded_id")
    def _compute_res_ids(self):
        res = super()._compute_res_ids()
        if self.env.context.get("message_forwarded_id"):
            # Set res_ids to the record to be forwarded
            # if the composer is set to forward a record
            # it sends the message to the record to be forwarded
            for composer in self.filtered(
                lambda c: c.forward_type == "another_thread" and c.forward_thread
            ):
                composer.res_ids = composer.forward_thread.ids
        return res

    @api.depends(
        "composition_mode",
        "model",
        "parent_id",
        "res_domain",
        "res_ids",
        "template_id",
        "forward_type",
    )
    @api.depends_context("message_forwarded_id")
    def _compute_partner_ids(self):
        # Save the partner_ids before calling super() to avoid losing them
        # because when template_id is not set,
        # partner_ids is set to False in the super() call.
        old_partners = {composer.id: composer.partner_ids for composer in self}
        res = super()._compute_partner_ids()
        if self.env.context.get("message_forwarded_id"):
            # Add the attachments from the original message.
            for composer in self:
                composer.partner_ids |= old_partners[composer.id]
        return res

    @api.model
    def get_record_data(self, values):
        result = super().get_record_data(values)
        re_prefix = _("Re:")
        fwd_prefix = _("Fwd:")
        if self.env.context.get("message_forwarded_id"):
            # remove 'Re: ' prefixes and add 'Fwd:' prefix to the subject
            subject = result.get("subject")
            if subject and subject.startswith(re_prefix):
                subject = f"{fwd_prefix} {subject[4:]}"
            result["subject"] = subject
        return result

    def _action_send_mail(self, auto_commit=False):
        return super(
            MailComposeMessage, self.with_context(forward_type=self.forward_type)
        )._action_send_mail(auto_commit=auto_commit)
