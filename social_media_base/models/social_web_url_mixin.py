# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SocialWebUrlMixin(models.AbstractModel):
    """Address a record has on the social media it belongs to.

    A record that mirrors something of a social media is also a page of the
    interface that social media serves, and the user expects the way back
    from Odoo. The address is not stored: it is derived from the reference
    the record already carries, so it cannot fall out of step with it and it
    costs nothing to the synchronization.

    A model joins by adding this mixin to its ``_inherit`` and redeclaring
    the dependencies of the computation; a connector only implements
    :meth:`_get_web_url` for its own social media.
    """

    _name = "social.web.url.mixin"
    _description = "Social Media Web Address"

    web_url = fields.Char(
        string="Web URL",
        compute="_compute_web_url",
        help="Address of this record on the social media.",
    )

    def _compute_web_url(self):
        for record in self:
            record.web_url = record._get_web_url()

    def _get_web_url(self):
        """Return the address of this record on the social media.

        Pure hook: the generic module knows no social media, so it answers
        nothing and the button stays hidden. Every connector overrides it
        for its own media type and chains to this one for the rest.

        :rtype: str
        """
        self.ensure_one()
        return ""

    def action_open_url(self):
        """Open this record on the social media, in a new tab."""
        self.ensure_one()
        if not self.web_url:
            return False
        return {
            "type": "ir.actions.act_url",
            "url": self.web_url,
            "target": "new",
        }
