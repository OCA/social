# -*- coding: utf-8 -*-
# Copyright 2017 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, fields, models


class FetchmailServer(models.Model):
    _inherit = "fetchmail.server"

    default_thread_id = fields.Reference(
        selection="_get_thread_models",
        string="Default mail thread",
        help="Messages with no clear route will be posted as a new message "
             "to this thread.",
    )

    @api.model
    def _get_thread_models(self):
        """Get list of available ``mail.thread`` submodels.

        :return [(model, name), ...]:
            Tuple list of available models that can receive messages.
        """
        models = self.env["ir.model.fields"].search([
            ("name", "=", "message_partner_ids"),
        ]).mapped("model_id")
        # Exclude AbstractModel
        return [(m.model, m.name) for m in models
                if getattr(self.env[m.model], "_auto")]

    # TODO New api on v10+
    # pylint: disable=old-api7-method-defined
    def onchange_server_type(self, cr, uid, ids, server_type=False, ssl=False,
                             object_id=False):
        """Remove :attr:`default_thread_id` if there is :attr:`object_id`."""
        result = super(FetchmailServer, self).onchange_server_type(
            cr, uid, ids, server_type, ssl, object_id,
        )
        if object_id:
            result["value"]["default_thread_id"] = False
        return result

    @api.multi
    @api.onchange("default_thread_id")
    def _onchange_remove_object_id(self):
        """Remove :attr:`object_id` if there is :attr:`default_thread_id`."""
        if self.default_thread_id:
            self.object_id = False
