# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SocialMedia(models.Model):
    """Social media supported by an installed connector module."""

    _name = "social.media"
    _inherit = "social.media.base.mixin"
    _description = "Social Media Supported by the System"

    name = fields.Char()
    description = fields.Text()
    media_type = fields.Selection(
        [],
        readonly=True,
    )
    image = fields.Binary()
    utm_medium_id = fields.Many2one(
        "utm.medium",
        string="UTM Medium",
        ondelete="restrict",
        help="Delivery method reported to the marketing campaigns for the "
        "links published on this social media. The connector module of each "
        "social media provides a default one.",
    )

    def action_open_account(self):
        """Open the wizard that associates an account of this social media.

        Pure hook: the base module knows no social media, so it returns
        nothing. Every connector module overrides it and returns the
        ``ir.actions.act_window`` of its own association wizard.
        """

    def _get_utm_medium(self):
        """Return the UTM medium reported for this social media.

        Connector modules override it to point at the medium of their own
        social media, which ``utm`` already ships for the usual ones.

        :rtype: recordset
        """
        self.ensure_one()
        return (
            self.utm_medium_id
            or self.env.ref(
                "social_media_base.utm_medium_social_media",
                raise_if_not_found=False,
            )
            or self.env["utm.medium"]
        )
