# -*- coding: utf-8 -*-
# © 2015 Antiun Ingeniería S.L. (http://www.antiun.com)
# © 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from openerp import exceptions
from openerp.http import local_redirect, request, route
from openerp.addons.mass_mailing.controllers.main import MassMailController
from .. import exceptions as _ex


class CustomUnsuscribe(MassMailController):
    def unsubscription_reason(self, mailing_id, email, res_id,
                              qcontext_extra=None):
        """Get the unsubscription reason form.

        :param mail.mass_mailing mailing_id:
            Mailing where the unsubscription is being processed.

        :param str email:
            Email to be unsubscribed.

        :param int res_id:
            ID of the unsubscriptor.

        :param dict qcontext_extra:
            Additional dictionary to pass to the view.
        """
        values = self.unsubscription_qcontext(mailing_id, email, res_id)
        values.update(qcontext_extra or dict())
        return request.website.render(
            "mass_mailing_custom_unsubscribe.reason_form",
            values)

    def unsubscription_qcontext(self, mailing_id, email, res_id):
        """Get rendering context for unsubscription form.

        :param mail.mass_mailing mailing_id:
            Mailing where the unsubscription is being processed.

        :param str email:
            Email to be unsubscribed.

        :param int res_id:
            ID of the unsubscriptor.
        """
        email_fname = origin_name = None
        domain = [("id", "=", res_id)]
        record_ids = request.env[mailing_id.mailing_model].sudo()

        if "email_from" in record_ids._fields:
            email_fname = "email_from"
        elif "email" in record_ids._fields:
            email_fname = "email"

        if email_fname and email:
            domain.append((email_fname, "ilike", email))
        else:
            # Trying to unsubscribe without email? Bad boy...
            raise exceptions.AccessDenied()

        if record_ids._name == "mail.mass_mailing.contact":
            domain.append(
                ("list_id", "in", mailing_id.contact_list_ids.ids))

        # Unsubscription targets
        record_ids = record_ids.search(domain)

        if not record_ids:
            # Trying to unsubscribe with fake criteria? Bad boy...
            raise exceptions.AccessDenied()

        # Special data to load for some models
        specials = {
            "mail.mass_mailing.contact": {
                "related": "list_id",
                "origin": "display_name",
            },
            "crm.lead": {
                "origin": "name",
                "contact": "contact_name",
            },
            "hr.applicant": {
                "related": "job_id",
                "origin": "name",
            },
            # In case you install OCA's event_registration_mass_mailing
            "event.registration": {
                "related": "event_id",
                "origin": "name",
            },
        }
        fnames = specials.get(record_ids._name, dict())

        # Get data to identify the source of the unsubscription
        first = record_ids[:1]
        contact_name = first[fnames.get("contact_fname", "name")]
        origin_model_name = request.env["ir.model"].search(
            [("model", "=", first._name)]).name
        try:
            first = first[fnames["related"]]
        except KeyError:
            pass
        try:
            origin_name = first[fnames["origin"]]
        except KeyError:
            pass

        # Get available reasons
        reason_ids = (
            request.env["mail.unsubscription.reason"].search([]))

        return {
            "contact_name": contact_name,
            "email": email,
            "mailing_id": mailing_id,
            "origin_model_name": origin_model_name,
            "origin_name": origin_name,
            "reason_ids": reason_ids,
            "record_ids": record_ids,
            "res_id": res_id,
        }

    @route(auth="public", website=True)
    def mailing(self, mailing_id, email=None, res_id=None, **post):
        """Display a confirmation form to get the unsubscription reason."""
        mailing = request.env["mail.mass_mailing"].sudo().browse(mailing_id)

        if not post.get("reason_id"):
            # We need to know why you leave, get to the form
            return self.unsubscription_reason(mailing, email, res_id)
        else:
            # Save reason and details
            try:
                with request.env.cr.savepoint():
                    record = request.env["mail.unsubscription"].sudo().create({
                        "email": email,
                        "unsubscriber_id": ",".join(
                            (mailing.mailing_model, res_id)),
                        "reason_id": int(post["reason_id"]),
                        "details": post.get("details", False),
                        "mass_mailing_id": mailing_id,
                    })

            # Should provide details, go back to form
            except _ex.DetailsRequiredError:
                return self.unsubscription_reason(
                    mailing, email, res_id,
                    {"error_details_required": True})

            # All is OK, unsubscribe
            result = super(CustomUnsuscribe, self).mailing(
                mailing_id, email, res_id, **post)
            record.success = result.data == "OK"

            # Redirect to the result
            path = "/page/mass_mailing_custom_unsubscribe.%s" % (
                "success" if record.success else "failure")
            return local_redirect(path)
