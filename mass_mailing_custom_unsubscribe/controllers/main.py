# Copyright 2015 Antiun Ingeniería S.L. (http://www.antiun.com)
# Copyright 2016 Tecnativa - Jairo Llopis
# Copyright 2020 Tecnativa - Pedro M. Baeza
# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.http import request, route

from odoo.addons.mass_mailing.controllers.main import MassMailController


class CustomUnsubscribe(MassMailController):
    def _mailing_unsubscribe_from_list(self, mailing, document_id, email, hash_token):
        self._add_extra_context(mailing, document_id)
        return super()._mailing_unsubscribe_from_list(
            mailing, document_id, email, hash_token
        )

    def _mailing_unsubscribe_from_document(
        self, mailing, document_id, email, hash_token
    ):
        self._add_extra_context(mailing, document_id)
        return super()._mailing_unsubscribe_from_document(
            mailing, document_id, email, hash_token
        )

    def _prepare_mailing_subscription_values(
        self, mailing, document_id, email, hash_token
    ):
        def show_list(lst):
            return not lst.not_cross_unsubscriptable or lst in mailing.contact_list_ids

        values = super()._prepare_mailing_subscription_values(
            mailing, document_id, email, hash_token
        )
        # Manage not_cross_unsubscriptable
        values["lists_contacts"] = values["lists_optin"].filtered(
            lambda x: show_list(x)
        )
        values["lists_optin"] = values["lists_optin"].filtered(lambda x: show_list(x))
        values["lists_optout"] = values["lists_optin"].filtered(lambda x: show_list(x))
        values["lists_public"] = values["lists_optin"].filtered(lambda x: show_list(x))
        return values

    @route()
    def mailing_update_list_subscription(
        self,
        mailing_id=None,
        document_id=None,
        email=None,
        hash_token=None,
        lists_optin_ids=None,
        **post,
    ):
        self._add_extra_context(mailing_id, document_id)
        return super().mailing_update_list_subscription(
            mailing_id, document_id, email, hash_token, lists_optin_ids, **post
        )

    @route()
    def mail_blocklist_add(
        self, mailing_id=None, document_id=None, email=None, hash_token=None
    ):
        self._add_extra_context(mailing_id, document_id)
        return super().mail_blocklist_add(mailing_id, document_id, email, hash_token)

    @route()
    def mail_blocklist_remove(
        self, mailing_id=None, document_id=None, email=None, hash_token=None
    ):
        self._add_extra_context(mailing_id, document_id)
        return super().mail_blocklist_remove(mailing_id, document_id, email, hash_token)

    @route()
    def mailing_send_feedback(
        self,
        mailing_id=None,
        document_id=None,
        email=None,
        hash_token=None,
        last_action=None,
        opt_out_reason_id=False,
        feedback=None,
        **post,
    ):
        self._add_extra_context(mailing_id, document_id, opt_out_reason_id, feedback)
        return super().mailing_send_feedback(
            mailing_id,
            document_id,
            email,
            hash_token,
            last_action,
            opt_out_reason_id,
            feedback,
            **post,
        )

    def _add_extra_context(self, mailing_id, res_id, reason_id=None, details=None):
        if not res_id:
            return
        environ = request.httprequest.headers.environ
        # Add mailing_id and res_id to request.context to be used in the
        # redefinition of _add and _remove methods of the mail.blacklist class
        extra_context = {
            "metadata": "\n".join(
                f"{val}: {environ.get(val)}"
                for val in ("REMOTE_ADDR", "HTTP_USER_AGENT", "HTTP_ACCEPT_LANGUAGE")
            ),
            "mailing_id": mailing_id,
            "unsubscription_res_id": int(res_id),
        }
        if reason_id:
            extra_context["reason_id"] = int(reason_id)
        if details:
            extra_context["details"] = details
        request.update_context(**extra_context)
