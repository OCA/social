# -*- coding: utf-8 -*-
# © 2015 Antiun Ingeniería S.L. (http://www.antiun.com)
# © 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from openerp import exceptions
from openerp.http import local_redirect, request, route
from openerp.addons.mass_mailing.controllers.main import MassMailController
from .. import exceptions as _ex


class CustomUnsubscribe(MassMailController):
    def _mailing_list_contacts_by_email(self, email):
        """Gets the mailing list contacts by email.

        This should not be displayed to the final user if security validations
        have not been matched.
        """
        return request.env["mail.mass_mailing.contact"].sudo().search([
            ("email", "=", email),
            ("opt_out", "=", False),
            ("list_id.not_cross_unsubscriptable", "=", False),
        ])

    def unsubscription_reason(self, mailing_id, email, res_id, token,
                              qcontext_extra=None):
        """Get the unsubscription reason form.

        :param mail.mass_mailing mailing_id:
            Mailing where the unsubscription is being processed.

        :param str email:
            Email to be unsubscribed.

        :param int res_id:
            ID of the unsubscriber.

        :param dict qcontext_extra:
            Additional dictionary to pass to the view.
        """
        values = self.unsubscription_qcontext(mailing_id, email, res_id, token)
        values.update(qcontext_extra or dict())
        return request.website.render(
            "mass_mailing_custom_unsubscribe.reason_form",
            values)

    def unsubscription_qcontext(self, mailing_id, email, res_id, token):
        """Get rendering context for unsubscription form.

        :param mail.mass_mailing mailing_id:
            Mailing where the unsubscription is being processed.

        :param str email:
            Email to be unsubscribed.

        :param int res_id:
            ID of the unsubscriber.
        """
        email_fname = origin_name = None
        domain = [("id", "=", res_id)]
        record_ids = request.env[mailing_id.mailing_model].sudo()

        if "email_from" in record_ids._fields:
            email_fname = "email_from"
        elif "email" in record_ids._fields:
            email_fname = "email"

        if not (email_fname and email):
            # Trying to unsubscribe without email? Bad boy...
            raise exceptions.AccessDenied()

        domain.append((email_fname, "ilike", email))

        # Search additional mailing lists for the unsubscriber
        additional_contacts = self._mailing_list_contacts_by_email(email)

        if record_ids._name == "mail.mass_mailing.contact":
            domain.append(
                ("list_id", "in", mailing_id.contact_list_ids.ids))

        # Unsubscription targets
        record_ids = record_ids.search(domain)

        if record_ids._name == "mail.mass_mailing.contact":
            additional_contacts -= record_ids

        if not record_ids:
            # Trying to unsubscribe with fake criteria? Bad boy...
            raise exceptions.AccessDenied()

        # Get data to identify the source of the unsubscription
        fnames = self.unsubscription_special_fnames(record_ids._name)
        first = record_ids[:1]
        contact_name = first[fnames.get("contact", "name")]
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
            "additional_contact_ids": additional_contacts,
            "contact_name": contact_name,
            "email": email,
            "mailing_id": mailing_id,
            "origin_model_name": origin_model_name,
            "origin_name": origin_name,
            "reason_ids": reason_ids,
            "record_ids": record_ids,
            "res_id": res_id,
            "token": token,
        }

    def unsubscription_special_fnames(self, model):
        """Define special field names to generate the unsubscription qcontext.

        :return dict:
            Special fields will depend on the model, so this method should
            return something like::

                {
                    "related": "parent_id",
                    "origin": "display_name",
                    "contact": "contact_name",
                }

            Where:

            - ``model.name`` is the technical name of the model.
            - ``related`` indicates the name of a field in ``model.name`` that
              contains a :class:`openerp.fields.Many2one` field which is
              considered what the user is unsubscribing from.
            - ``origin``: is the name of the field that contains the name of
              what the user is unsubscribing from.
            - ``contact`` is the name of the field that contains the name of
              the user that is unsubscribing.

            Missing keys will mean that nothing special is required for that
            model and it will use the default values.
        """
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
        return specials.get(model, dict())

    @route(auth="public", website=True)
    def mailing(self, mailing_id, email=None, res_id=None, **post):
        """Display a confirmation form to get the unsubscription reason."""
        mailing = request.env["mail.mass_mailing"]
        path = "/page/mass_mailing_custom_unsubscribe.%s"
        good_token = mailing.hash_create(mailing_id, res_id, email)

        # Trying to unsubscribe with fake hash? Bad boy...
        if good_token and post.get("token") != good_token:
            return local_redirect(path % "failure")

        mailing = mailing.sudo().browse(mailing_id)
        contact = request.env["mail.mass_mailing.contact"].sudo()
        unsubscription = request.env["mail.unsubscription"].sudo()

        if not post.get("reason_id"):
            # We need to know why you leave, get to the form
            return self.unsubscription_reason(
                mailing, email, res_id, post.get("token"))

        # Save reason and details
        try:
            with request.env.cr.savepoint():
                records = unsubscription.create({
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
                mailing, email, res_id, post.get("token"),
                {"error_details_required": True})

        # Unsubscribe from additional lists
        for key, value in post.iteritems():
            try:
                label, list_id = key.split(",")
                if label != "list_id":
                    raise ValueError
                list_id = int(list_id)
            except ValueError:
                pass
            else:
                contact_id = contact.browse(int(value))
                if contact_id.list_id.id == list_id:
                    contact_id.opt_out = True
                    records += unsubscription.create({
                        "email": email,
                        "unsubscriber_id": ",".join((contact._name, value)),
                        "reason_id": int(post["reason_id"]),
                        "details": post.get("details", False),
                        "mass_mailing_id": mailing_id,
                    })

        # All is OK, unsubscribe
        result = super(CustomUnsubscribe, self).mailing(
            mailing_id, email, res_id, **post)
        records.write({"success": result.data == "OK"})

        # Redirect to the result
        return local_redirect(path % ("success" if result.data == "OK"
                                      else "failure"))
