# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SocialStage(models.Model):
    """Status of a campaign, a campaign group or an ad on a social media.

    Every social media names its statuses its own way, so instead of a
    hardcoded selection each connector module declares the stages of its
    social media as data. ``code`` holds the value returned by the social
    media, which is what the connector maps when it imports.
    """

    _name = "social.stage"
    _description = "Social Stage"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        help="Status value as returned by the social media, used by the "
        "connector module to map the remote status to this stage.",
    )
    media_id = fields.Many2one(
        "social.media",
        required=True,
        index=True,
        ondelete="cascade",
    )
    applies_to = fields.Selection(
        [
            ("campaign", "Campaign"),
            ("group", "Campaign Group"),
            ("ad", "Ad"),
        ],
        required=True,
        default="campaign",
        help="Records this stage can be set on.",
    )
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(
        help="Fold the column of this stage in the kanban views.",
    )
    level = fields.Selection(
        [
            ("success", "Success"),
            ("info", "Info"),
            ("warning", "Warning"),
            ("danger", "Danger"),
            ("secondary", "Secondary"),
        ],
        default="secondary",
        help="Colour of the badge showing this stage.",
    )

    _sql_constraints = [
        (
            "code_uniq",
            "unique(media_id, applies_to, code)",
            "The stage code must be unique per social media and scope.",
        ),
    ]

    @api.model
    def _get_stage(self, media_type, applies_to, code):
        """Return the stage matching a status code of a social media.

        :param media_type: technical media type of the social media.
        :param applies_to: ``campaign``, ``group`` or ``ad``.
        :param code: status value as returned by the social media.
        :return: the stage, empty when the connector has not declared it.
        :rtype: recordset
        """
        if not (media_type and applies_to and code):
            return self.browse()
        return self.search(
            [
                ("media_id.media_type", "=", media_type),
                ("applies_to", "=", applies_to),
                ("code", "=", code),
            ],
            limit=1,
        )
