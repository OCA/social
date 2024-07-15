# Copyright 2015 Antiun Ingeniería S.L. (http://www.antiun.com)
# Copyright 2016 Tecnativa - Jairo Llopis
# Copyright 2020 Tecnativa - Pedro M. Baeza
# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.http import request, route

from odoo.addons.mass_mailing.controllers.main import MassMailController


class CustomUnsubscribe(MassMailController):
    def _mailing_unsubscribe_from_list(self, mailing, document_id, email, hash_token):
        self._add_metadata()
        return super()._mailing_unsubscribe_from_list(
            mailing, document_id, email, hash_token
        )

    def _mailing_unsubscribe_from_document(
        self, mailing, document_id, email, hash_token
    ):
        self._add_metadata()
        return super()._mailing_unsubscribe_from_document(
            mailing, document_id, email, hash_token
        )

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
        self._add_metadata()
        return super().mailing_update_list_subscription(
            mailing_id, document_id, email, hash_token, lists_optin_ids, **post
        )

    @route()
    def mail_blocklist_add(
        self, mailing_id=None, document_id=None, email=None, hash_token=None
    ):
        self._add_metadata()
        return super().mail_blocklist_add(mailing_id, document_id, email, hash_token)

    @route()
    def mail_blocklist_remove(
        self, mailing_id=None, document_id=None, email=None, hash_token=None
    ):
        self._add_metadata()
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
        self._add_metadata()
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

    def _add_metadata(self):
        extra_context = {
            "metadata": "\n".join(
                f"{val}: {request.httprequest.headers.environ.get(val)}"
                for val in ("REMOTE_ADDR", "HTTP_USER_AGENT", "HTTP_ACCEPT_LANGUAGE")
            ),
        }
        request.update_context(**extra_context)
