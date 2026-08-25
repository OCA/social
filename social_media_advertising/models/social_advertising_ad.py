# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class SocialAdvertisingAd(models.Model):
    """Ad served by a social media, as the social media reports it.

    These records mirror what the social media answers: the connector
    modules create and refresh them with :meth:`social.account._sync_ads`
    and nothing is ever pushed back. They exist so the ads can be searched,
    filtered and grouped with the standard views instead of being listed
    live, which is what lets a user filter them by creation date, group
    them by campaign or save a favourite.

    The statistics are the ones of the window the last synchronization
    asked for, kept in ``statistics_date_from`` and ``statistics_date_to``:
    a figure without its window cannot be read.

    Only the fields every advertising platform has are declared here. What
    belongs to a single social media is added by its connector module.
    """

    _name = "social.advertising.ad"
    _description = "Social Advertising Ad"
    _order = "created_date desc, id desc"

    name = fields.Char(
        compute="_compute_name",
        store=True,
        help="Text of the promoted post, or a note saying it is not "
        "available when the ad promotes a post this database does not know.",
    )
    active = fields.Boolean(
        default=True,
        help="Ads that disappear from the social media are archived instead "
        "of deleted, so their statistics are not lost.",
    )
    remote_ref = fields.Char(
        string="Remote Reference",
        required=True,
        index=True,
        copy=False,
        help="Identifier of this ad on the social media.",
    )
    account_id = fields.Many2one(
        "social.account",
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="account_id.company_id",
        store=True,
        index=True,
    )
    media_id = fields.Many2one(related="account_id.media_id", store=True)
    media_type = fields.Selection(related="media_id.media_type")
    user_id = fields.Many2one(
        related="account_id.user_id",
        string="Responsible",
        store=True,
        index=True,
        help="Responsible user of the account this ad belongs to. Only that "
        "user and the social media administrators can see it.",
    )
    advertising_account_id = fields.Many2one(
        "social.advertising.account",
        index=True,
        ondelete="set null",
        help="Advertising account this ad was served from.",
    )
    advertising_account_is_current = fields.Boolean(
        related="advertising_account_id.is_current",
        string="Advertising Account In Use",
        store=True,
        help="Whether the advertising account this ad belongs to is the one "
        "the social media account works with right now. Ads of the other "
        "advertising accounts are kept as they were last synchronized.",
    )
    campaign_id = fields.Many2one(
        "social.advertising.campaign",
        string="Campaign",
        index=True,
        ondelete="set null",
        help="Campaign of the social media this ad belongs to.",
    )
    post_account_id = fields.Many2one(
        "social.post.account",
        string="Publication",
        index=True,
        ondelete="set null",
        help="Publication this ad promotes. It is empty when the promoted "
        "post was not created nor imported into this database.",
    )
    stage_id = fields.Many2one(
        "social.stage",
        string="Status",
        index=True,
        domain="[('media_id', '=', media_id), ('applies_to', '=', 'ad')]",
        help="Status of this ad on the social media.",
    )
    stage_level = fields.Selection(related="stage_id.level")
    stage_code = fields.Char(
        related="stage_id.code",
        help="Technical field: status code of the social media, used by the "
        "connector modules to tell their own statuses apart in the views.",
    )
    status_detail = fields.Char(
        help="Reason the social media gives for serving this ad or not.",
    )
    created_date = fields.Datetime(
        string="Created On",
        help="Moment the ad was created on the social media.",
    )
    impression_count = fields.Integer()
    click_count = fields.Integer()
    action_click_count = fields.Integer(
        help="Clicks on the call to action of the ad.",
    )
    ad_unit_click_count = fields.Integer(
        help="Clicks anywhere on the ad unit itself.",
    )
    conversion_count = fields.Integer()
    cost = fields.Monetary()
    currency_id = fields.Many2one(
        "res.currency",
        help="Currency the cost is expressed in. It is the one the social "
        "media reports, which is not necessarily the one the advertising "
        "account is billed in: LinkedIn, for instance, always answers in US "
        "dollars.",
    )
    statistics_date_from = fields.Date(
        string="Statistics From",
        help="First day of the window the statistics of this ad cover.",
    )
    statistics_date_to = fields.Date(
        string="Statistics To",
        help="Last day of the window the statistics of this ad cover.",
    )
    last_sync_date = fields.Datetime(string="Last Fetch", readonly=True)
    url = fields.Char(
        string="Ad URL",
        help="Address of this ad on the social media. It opens the ad "
        "itself, not the campaign it belongs to.",
    )
    can_delete_remote_ad = fields.Boolean(
        compute="_compute_can_delete_remote_ad",
        help="Technical field: whether the connector module of this social "
        "media deletes an ad, and this one is not gone already.",
    )

    _sql_constraints = [
        (
            "remote_ref_account_uniq",
            "unique(account_id, remote_ref)",
            "An ad can only be linked once to a social media account.",
        ),
    ]

    @api.depends("post_account_id.message")
    def _compute_name(self):
        """Name the ad after the post it promotes.

        An ad has no name of its own on the social media, and the text of
        the promoted post is what the user recognizes it by. An ad whose
        post this database does not know says so instead: the remote
        reference names nothing to the user.
        """
        for ad in self:
            message = (ad.post_account_id.message or "").strip()
            ad.name = message or _("Post not available")

    def _compute_can_delete_remote_ad(self):
        """Whether this ad can be deleted, answered by each connector.

        Nothing is deletable by default: an ad is a mirror of the social
        media, and only a connector knows whether its API deletes one.
        """
        self.can_delete_remote_ad = False

    def action_delete_remote_ad(self):
        """Delete this ad on the social media.

        The ads mirror the social media and a regular user only reads them,
        so the permission checked is the one of the account they belong to:
        its responsible user and the social media administrators. The local
        record is written with ``sudo()`` afterwards, like the
        synchronization does.

        :return: a notification describing what the social media did.
        :rtype: dict
        """
        self.ensure_one()
        if not self.account_id.can_manage_account:
            raise AccessError(
                _(
                    "Only the responsible user of the account %(account)s and "
                    "the social media administrators may delete its ads.",
                    account=self.account_id.display_name,
                )
            )
        return self._delete_remote_ad()

    def _delete_remote_ad(self):
        """Delete the ad on the social media, implemented by each connector.

        :return: a notification describing what the social media did.
        :rtype: dict
        """
        raise UserError(_("Deleting an ad is not available for this social media."))

    def _register_remote_ad_gone(self):
        """Record that the social media does not answer these ads anymore.

        They are archived, never deleted: their statistics are the only
        trace left of what they did. Connectors extend it to leave the
        status their social media gives a deleted ad, so an archived ad does
        not keep showing the last status it was fetched with.
        """
        self.write({"active": False})

    def action_purge_ad(self):
        """Delete this ad and its history from Odoo.

        Reserved to the archived ads: one the social media still answers
        would be created again by the next synchronization, so deleting it
        only loses its statistics for nothing.

        :return: the list of ads, since the record it was called on is gone.
        :rtype: dict
        """
        self.ensure_one()
        if self.active:
            raise UserError(
                _(
                    "Only an ad the social media no longer serves can be "
                    "deleted here. This one is still answered, so the next "
                    "synchronization would create it again."
                )
            )
        media_type = self.media_type
        self.unlink()
        return self._advertising_ad_action(media_type)

    @api.model
    def _advertising_ad_action(self, media_type=None):
        """Return the list of ads to fall back to when the record is gone.

        Connector modules answer with the list of their own social media, so
        the user is left where the ad was. The media type is an argument
        because the record is already unlinked when this is needed.

        :param media_type: media type of the ad that is gone.
        :rtype: dict
        """
        return self.env["ir.actions.act_window"]._for_xml_id(
            "social_media_advertising.social_advertising_ad_action"
        )

    def _notify_remote_ad_deleted(self, message, gone, media_type=None):
        """Report what the social media did with the deletion.

        :param message: what to tell the user.
        :param gone: whether the ad is gone and its record with it, in which
            case the form it was opened from cannot be reloaded and the list
            of ads is opened instead.
        :param media_type: media type of the ad, needed to open the right
            list once the record is gone.
        :rtype: dict
        """
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": message,
                "next": self._advertising_ad_action(media_type)
                if gone
                else {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    def action_open_url(self):
        """Open this ad on the social media."""
        self.ensure_one()
        if not self.url:
            return False
        return {
            "type": "ir.actions.act_url",
            "url": self.url,
            "target": "new",
        }

    def action_open_post_account(self):
        """Open the publication this ad promotes."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Publication"),
            "res_model": "social.post.account",
            "res_id": self.post_account_id.id,
            "view_mode": "form",
            "views": [
                (
                    self.env.ref("social_media_base.social_post_account_view_form").id,
                    "form",
                )
            ],
        }
