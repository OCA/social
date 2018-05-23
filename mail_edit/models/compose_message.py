# -*- coding: utf-8 -*-
# © 2016 Sunflower IT (http://sunflowerweb.nl)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model
    def _get_model_selection(self):
        """Get allowed models and their names."""
        model_objs = self.env["res.request.link"].search(
            [("mail_edit", "=", True)],
            order="name")
        return [(m.object, m.name) for m in model_objs]

    @api.one
    @api.onchange("destination_object_id")
    def change_destination_object(self):
        """Update some fields for the new message."""
        # pylint: disable=api-one-deprecated
        if self.destination_object_id:
            self.model = self.destination_object_id._name
            self.res_id = self.destination_object_id.id

            model_name = self.env["ir.model"].search([
                ("model", "=", self.model)]).name
            display_name = self.destination_object_id.display_name
            if model_name:
                display_name = "%s %s" % (model_name, display_name)

            self.record_name = display_name
        else:
            self.model = self.res_id = self.record_name = False

    destination_object_id = fields.Reference(
        _get_model_selection,
        "Destination object",
        help="Object where the message will be moved to")

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        res = super(MailMessage, self)._message_read_dict_postprocess(
            messages, message_tree)
        for message_dict in messages:
            # Check if current user is a superuser
            if self.env.user.has_group('mail_edit.group_mail_edit_superuser'):
                message_dict['is_superuser'] = True
        return res
