# -*- coding: utf-8 -*-
# Copyright 2015 Antiun Ingeniería S.L. (http://www.antiun.com)
# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from openerp.http import request, route
from openerp.addons.website_mass_mailing.controllers.main \
    import MassMailController

_logger = logging.getLogger(__name__)


class CustomUnsubscribe(MassMailController):
    def reason_form(self, mailing, email, res_id, token):
        """Get the unsubscription reason form.

        :param mail.mass_mailing mailing:
            Mailing where the unsubscription is being processed.

        :param str email:
            Email to be unsubscribed.

        :param int res_id:
            ID of the unsubscriber.

        :param str token:
            Security token for unsubscriptions.
        """
        reasons = request.env["mail.unsubscription.reason"].search([])
        return request.website.render(
            "mass_mailing_custom_unsubscribe.reason_form",
            {
                "email": email,
                "mailing": mailing,
                "reasons": reasons,
                "res_id": res_id,
                "token": token,
            })

    @route()
    def mailing(self, mailing_id, email=None, res_id=None, token="", **post):
        """Ask/save unsubscription reason."""
        _logger.debug(
            "Called `mailing()` with: %r",
            (mailing_id, email, res_id, token, post))
        mailing = request.env["mail.mass_mailing"].sudo().browse(mailing_id)
        mailing._unsubscribe_token(res_id, token)
        # Mass mailing list contacts are a special case because they have a
        # subscription management form
        if mailing.mailing_model == 'mail.mass_mailing.contact':
            result = super(CustomUnsubscribe, self).mailing(
                mailing_id, email, res_id, **post)
            # FIXME Remove res_id and token in version where this is merged:
            # https://github.com/odoo/odoo/pull/14385
            result.qcontext.update({
                "token": token,
                "res_id": res_id,
                "contacts": result.qcontext["contacts"].filtered(
                    lambda contact:
                        not contact.list_id.not_cross_unsubscriptable or
                        contact.list_id <= mailing.contact_list_ids
                ),
                "reasons":
                    request.env["mail.unsubscription.reason"].search([]),
            })
            return result
        # Any other record type gets a simplified form
        try:
            # Check if we already have a reason for unsubscription
            reason_id = int(post["reason_id"])
        except (KeyError, ValueError):
            # No reasons? Ask for them
            return self.reason_form(mailing, email, res_id, token)
        else:
            # Unsubscribe, saving reason and details by context
            request.context.update({
                "default_reason_id": reason_id,
                "default_details": post.get("details") or False,
            })
            del request.env
            # You could get a DetailsRequiredError here, but only if HTML5
            # validation fails, which should not happen in modern browsers
            return super(CustomUnsubscribe, self).mailing(
                mailing_id, email, res_id, **post)

    @route()
    def unsubscribe(self, mailing_id, opt_in_ids, opt_out_ids, email, res_id,
                    token, reason_id=None, details=None):
        """Store unsubscription reasons when unsubscribing from RPC."""
        # Update request context and reset environment
        if reason_id:
            request.context["default_reason_id"] = int(reason_id)
            request.context["default_details"] = details or False
        # FIXME Remove token check in version where this is merged:
        # https://github.com/odoo/odoo/pull/14385
        mailing = request.env['mail.mass_mailing'].sudo().browse(mailing_id)
        mailing._unsubscribe_token(res_id, token)
        _logger.debug(
            "Called `unsubscribe()` with: %r",
            (mailing_id, opt_in_ids, opt_out_ids, email, res_id, token,
             reason_id, details))
        return super(CustomUnsubscribe, self).unsubscribe(
            mailing_id, opt_in_ids, opt_out_ids, email)
