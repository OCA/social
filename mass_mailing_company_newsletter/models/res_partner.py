# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = "res.partner"

    main_mailing_list_id = fields.Many2one(
        comodel_name="mailing.list",
        string="Company Newsletter",
        help="Technical field: The company's Newsletter mailing list.",
        compute="_compute_main_mailing_list_id",
        compute_sudo=True,
    )
    main_mailing_list_subscription_id = fields.Many2one(
        comodel_name="mailing.contact.subscription",
        string="Company Newsletter Subscription",
        help="Technical field: The company's newsletter subscription for this partner.",
        compute="_compute_main_mailing_list_subscription_id",
        compute_sudo=True,
        search="_search_main_mailing_list_subscription_id",
    )
    main_mailing_list_subscription_state = fields.Selection(
        string="Company Newsletter Subscription State",
        selection=[
            ("subscribed", "Subscribed"),
            ("unsubscribed", "Unsubscribed"),
        ],
        compute="_compute_main_mailing_list_subscription_state",
        compute_sudo=True,
        inverse="_inverse_main_mailing_list_subscription_state",
        search="_search_main_mailing_list_subscription_state",
        tracking=True,
    )
    main_mailing_list_subscription_date = fields.Datetime(
        related="main_mailing_list_subscription_id.subscription_date",
        string="Company Newsletter Subscription Date",
    )
    main_mailing_list_unsubscription_date = fields.Datetime(
        related="main_mailing_list_subscription_id.unsubscription_date",
        string="Company Newsletter Unsubscription Date",
    )

    @api.depends("company_id")
    @api.depends_context("company")
    def _compute_main_mailing_list_id(self):
        self.main_mailing_list_id = self.env.company.main_mailing_list_id

    @api.depends("mailing_contact_id")
    @api.depends_context("company")
    def _compute_main_mailing_list_subscription_id(self):
        if not self.main_mailing_list_id or not self.mailing_contact_id:
            self.main_mailing_list_subscription_id = False
            return
        # Find the mailing.contact.subscription
        subs = self.env["mailing.contact.subscription"].search(
            [
                ("contact_id", "in", self.mailing_contact_id.ids),
                ("list_id", "=", self.main_mailing_list_id.id),
            ]
        )
        subs_by_contact_id = {sub.contact_id.id: sub.id for sub in subs}
        for rec in self:
            rec.main_mailing_list_subscription_id = subs_by_contact_id.get(
                rec.mailing_contact_id.id
            )

    def _search_main_mailing_list_subscription_id(self, operator, value):
        # Functionally speaking, this shouldn't be necessary.
        # But without it, Odoo would print an error log saying:
        # Non-stored field main_mailing_list_subscription_id cannot be searched.
        # Even though we're not explicitly searching on it, the following line is:
        # https://github.com/odoo/odoo/blob/c9b6b030f/odoo/models.py#L5860
        if operator != "in":  # pragma: no cover
            return NotImplementedError()
        # Rely on the fact that search takes a query as value since Odoo 14.0
        # See https://github.com/odoo/odoo/commit/69869ab68
        mailing_list = self.env.company.main_mailing_list_id
        search = self.env["mailing.contact.subscription"]._search(
            [
                ("list_id", "=", mailing_list.id),
                ("id", "in", value),
            ]
        )
        return [("mailing_contact_id.subscription_list_ids", "in", search)]

    @api.depends("main_mailing_list_subscription_id.opt_out")
    def _compute_main_mailing_list_subscription_state(self):
        """Compute mass mailing state

        There are basically 3 possible values:
        * False: The mailing.contact.subscription record doesn't exist.
        * Subscribed: The subscription exists and it's active.
        * Unsubscribed: The subscription exists and but it's opt_out.
        """
        for rec in self:
            if not rec.main_mailing_list_subscription_id:
                rec.main_mailing_list_subscription_state = False
            elif rec.main_mailing_list_subscription_id.opt_out:
                rec.main_mailing_list_subscription_state = "unsubscribed"
            else:
                rec.main_mailing_list_subscription_state = "subscribed"

    def _search_main_mailing_list_subscription_state(self, operator, value):
        if operator != "=" or value not in [False, "subscribed", "unsubscribed"]:
            # pragma: no cover
            raise NotImplementedError()
        mailing_list = self.env.company.main_mailing_list_id
        # No company newsletter
        if not mailing_list:  # pragma: no cover
            return expression.TRUE_DOMAIN if value is False else expression.FALSE_DOMAIN
        # Registration is not set
        if value is False:
            return [
                "|",
                ("mailing_contact_id", "=", False),
                ("mailing_contact_id.list_ids", "!=", mailing_list.id),
            ]
        # Rely on the fact that search takes a query as value since Odoo 14.0
        # See https://github.com/odoo/odoo/commit/69869ab68
        search = self.env["mailing.contact.subscription"]._search(
            [
                ("list_id", "=", mailing_list.id),
                ("opt_out", "=", False if value == "subscribed" else True),
            ]
        )
        return [("mailing_contact_id.subscription_list_ids", "in", search)]

    def _inverse_main_mailing_list_subscription_state(self):
        if not self.env.company.main_mailing_list_id:  # pragma: no cover
            raise ValidationError(
                _(
                    "You need to configure a main newsletter for company '%s'.\n"
                    "To do so, go to Mass Mailing general settings."
                )
            )
        for rec in self:
            value = rec.main_mailing_list_subscription_state
            contact = rec.mailing_contact_id
            subscription = rec.main_mailing_list_subscription_id
            # Setting back to null: remove subscription record
            if value is False:
                subscription.unlink()
                continue
            # Create contact if it's missing
            if not contact:
                rec._create_mailing_contact()
            # Update or create subscription
            if not subscription:
                if value == "subscribed":
                    rec._create_mailing_contact_subscription()
                else:
                    rec._create_mailing_contact_subscription(opt_out=True)
            else:
                if value == "subscribed":
                    subscription.opt_out = False
                elif value == "unsubscribed":
                    subscription.opt_out = True

    def _create_mailing_contact(self):
        self.ensure_one()
        if not self.email:  # pragma: no cover
            raise ValidationError(_("Email is required to subscribe to the Newsletter"))
        return (
            self.env["mailing.contact"]
            .sudo()
            .create(
                {
                    "name": self.name or self.email,
                    "email": self.email,
                    "title_id": self.title.id,
                    "country_id": self.country_id.id,
                    "tag_ids": [(6, 0, self.category_id.ids)],
                }
            )
        )

    def _create_mailing_contact_subscription(self, **kwargs):
        self.ensure_one()
        assert self.mailing_contact_id
        assert self.env.company.main_mailing_list_id
        vals = {
            "contact_id": self.mailing_contact_id.id,
            "list_id": self.env.company.main_mailing_list_id.id,
        }
        if kwargs is not None:
            vals.update(kwargs)
        subs = self.env["mailing.contact.subscription"].sudo().create(vals)
        self.invalidate_cache(["main_mailing_list_subscription_id"])
        return subs
