# -*- coding: utf-8 -*-
# © 2014-2015 Grupo ESOC <www.grupoesoc.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models


class MailForwardComposeMessage(models.TransientModel):
    """Allow forwarding a message.

    It duplicates the message and optionally attaches it to another object
    of the database and sends it to another recipients than the original one.
    """
    _name = "mail_forward.compose_message"
    _inherits = {"mail.compose.message": "original_wizard_id"}

    @api.model
    def default_get(self, fields):
        """Fix default values.

        Sometimes :meth:`openerp.addons.mail.mail_compose_message
        .mail_compose_message.default_get` overwrites the default value
        for the ``subject`` field, even when it gets the right default value
        from the context.

        This method fixes that by getting it from the context if available.
        """
        result = self.original_wizard_id.default_get(fields)

        if "subject" in result and "default_subject" in self.env.context:
            result["subject"] = self.env.context["default_subject"]

        return result

    @api.model
    def _get_model_selection(self):
        """Get allowed models and their names."""
        model_objs = self.env["res.request.link"].search(
            [("mail_forward_target", "=", True)],
            order="name")
        return [(m.object, m.name) for m in model_objs]

    @api.one
    @api.onchange("destination_object_id")
    def change_destination_object(self):
        """Update some fields for the new message."""
        if self.destination_object_id:
            self.model = self.destination_object_id._name
            self.res_id = self.destination_object_id.id

            model_name = (self.env["ir.model"]
                          .search([("model", "=", self.model)])
                          .name)
            record_name = self.destination_object_id.name_get()[0][1]
            if model_name:
                record_name = "%s %s" % (model_name, record_name)

            self.record_name = record_name
        else:
            self.model = self.res_id = self.record_name = False

    @api.one
    def send_mail(self):
        """Send mail and execute the attachment relocation if needed."""
        # Let the original wizard do de hard work
        result = self.original_wizard_id.send_mail()

        # Relocate attachments if needed
        if (self.move_attachments and
                self.model and
                self.res_id and
                self.attachment_ids):
            for attachment in self.attachment_ids:
                attachment.res_model = self.model
                attachment.res_id = self.res_id

        return result

    destination_object_id = fields.Reference(
        _get_model_selection,
        "Destination object",
        help="Object where the forwarded message will be attached")

    move_attachments = fields.Boolean(
        "Move attachments",
        help="Attachments will be assigned to the chosen destination "
             "object and you will be able to pick them from its "
             "'Attachments' button, but they will not be there for "
             "the current object if any. In any case you can always "
             "open it from the message itself.")

    original_wizard_id = fields.Many2one(
        "mail.compose.message",
        "Original message compose wizard",
        delegate=True,
        ondelete="cascade",
        required=True)
