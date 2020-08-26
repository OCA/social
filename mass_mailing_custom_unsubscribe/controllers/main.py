# Copyright 2015 Antiun Ingeniería S.L. (http://www.antiun.com)
# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.http import request, route

from odoo.addons.mass_mailing.controllers.main import MassMailController

_logger = logging.getLogger(__name__)


class CustomUnsubscribe(MassMailController):
    def reason_form(self, mailing_id, email, res_id, reasons, token):
        """Get the unsubscription reason form.

        :param mailing.mailing mailing:
            Mailing where the unsubscription is being processed.

        :param str email:
            Email to be unsubscribed.

        :param int res_id:
            ID of the unsubscriber.

        :param str token:
            Security token for unsubscriptions.
        """
        return request.render(
            "mass_mailing_custom_unsubscribe.reason_form",
            {
                "email": email,
                "mailing_id": mailing_id,
                "reasons": reasons,
                "res_id": res_id,
                "token": token,
            },
        )

    @route()
    def mailing(self, mailing_id, email=None, res_id=None, token="", **post):
        """Ask/save unsubscription reason."""
        _logger.debug(
            "Called `mailing()` with: %r", (mailing_id, email, res_id, token, post)
        )
        reasons = request.env["mail.unsubscription.reason"].search([])
        if not res_id:
            res_id = "0"
        res_id = res_id and int(res_id)
        try:
            # Check if we already have a reason for unsubscription
            reason_id = int(post["reason_id"])
        except (KeyError, ValueError):
            # No reasons? Ask for them
            return self.reason_form(mailing_id, email, res_id, reasons, token)
        else:
            # Unsubscribe, saving reason and details by context
            details = post.get("details", False)
            self._add_extra_context(mailing_id, res_id, reason_id, details)
            mailing_obj = request.env["mailing.mailing"]
            mass_mailing = mailing_obj.sudo().browse(mailing_id)
            model = mass_mailing.mailing_model_real
            if "opt_out" in request.env[model]._fields and model != "mailing.contact":
                mass_mailing.update_opt_out_other(email, [res_id], True)
                result = request.render(
                    "mass_mailing.page_unsubscribed",
                    {
                        "email": email,
                        "mailing_id": mailing_id,
                        "res_id": res_id,
                        "show_blacklist_button": request.env["ir.config_parameter"]
                        .sudo()
                        .get_param("mass_mailing.show_blacklist_buttons"),
                    },
                )
                result.qcontext.update({"reasons": reasons})
            else:
                # You could get a DetailsRequiredError here, but only if HTML5
                # validation fails, which should not happen in modern browsers
                result = super().mailing(mailing_id, email, res_id, token=token, **post)
                if model == "mailing.contact":
                    # update list_ids taking into account
                    # not_cross_unsubscriptable field
                    result.qcontext.update(
                        {
                            "reasons": reasons,
                            "list_ids": result.qcontext["list_ids"].filtered(
                                lambda m_list: not m_list.not_cross_unsubscriptable
                                or m_list in mass_mailing.contact_list_ids
                            ),
                        }
                    )
            return result

    @route()
    def unsubscribe(
        self,
        mailing_id,
        opt_in_ids,
        opt_out_ids,
        email,
        res_id,
        token,
        reason_id=None,
        details=None,
    ):
        """Store unsubscription reasons when unsubscribing from RPC."""
        # Update request context
        self._add_extra_context(mailing_id, res_id, reason_id, details)
        _logger.debug(
            "Called `unsubscribe()` with: %r",
            (
                mailing_id,
                opt_in_ids,
                opt_out_ids,
                email,
                res_id,
                token,
                reason_id,
                details,
            ),
        )
        return super().unsubscribe(
            mailing_id, opt_in_ids, opt_out_ids, email, res_id, token
        )

    @route()
    def blacklist_add(
        self, mailing_id, res_id, email, token, reason_id=None, details=None
    ):
        self._add_extra_context(mailing_id, res_id, reason_id, details)
        return super().blacklist_add(mailing_id, res_id, email, token)

    @route()
    def blacklist_remove(
        self, mailing_id, res_id, email, token, reason_id=None, details=None
    ):
        self._add_extra_context(mailing_id, res_id, reason_id, details)
        return super().blacklist_remove(mailing_id, res_id, email, token)

    def _add_extra_context(self, mailing_id, res_id, reason_id, details):
        environ = request.httprequest.headers.environ
        # Add mailing_id and res_id to request.context to be used in the
        # redefinition of _add and _remove methods of the mail.blacklist class
        extra_context = {
            "default_metadata": "\n".join(
                "{}: {}".format(val, environ.get(val))
                for val in ("REMOTE_ADDR", "HTTP_USER_AGENT", "HTTP_ACCEPT_LANGUAGE")
            ),
            "mailing_id": mailing_id,
            "unsubscription_res_id": int(res_id),
        }
        if reason_id:
            extra_context["default_reason_id"] = int(reason_id)
        if details:
            extra_context["default_details"] = details
        request.context = dict(request.context, **extra_context)
