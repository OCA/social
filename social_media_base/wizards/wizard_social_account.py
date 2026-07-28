# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class WizardSocialAccount(models.TransientModel):
    _name = "wizard.social.account"
    _inherit = ["social.media.base.mixin"]
    _description = "Associate Social Media Account"

    account_id = fields.Many2one("social.account")
    media_id = fields.Many2one("social.media", required=True)
    media_type = fields.Selection(
        string="Media Type",
        related="media_id.media_type",
    )
    update_keys = fields.Boolean(
        default=False, help="Only enable this field if your credentials have changed"
    )
    update_token = fields.Boolean(default=False, help="Update token")
    image = fields.Binary(related="media_id.image")
    csrf_state_token = fields.Char(
        readonly=True,
        help="Anti-CSRF state token used during the OAuth flow.",
    )

    def _get_csrf_state_token(self):
        """Return the anti-CSRF state token of the OAuth flow.

        Connector modules override it when their social media exchanges
        information during the authorization process.
        """

    def _compute_csrf_state_token(self):
        """Store the anti-CSRF state token of the OAuth flow."""
        for media in self:
            media.csrf_state_token = media._get_csrf_state_token()

    def _get_url_redirect(self):
        """Return the OAuth callback URL, implemented by each connector."""

    def _action_add_account(self):
        """Redirect to the authorization page of the social network.

        Connector modules override it and keep the state token computed
        here to exchange the credentials and the access token.
        """
        self._compute_csrf_state_token()

    def _action_valid_add_account(self):
        """Validate the wizard before requesting access to the social network."""
        return True

    def _check_account_access(self):
        """Check the user may act on the account targeted by the wizard.

        The connectors write the credentials with ``sudo()``, which skips
        the record rules, so ownership is checked here instead.
        """
        for wizard in self:
            if wizard.account_id:
                wizard.account_id._check_can_associate()

    def action_associate_social_account(self):
        """Link the account with the social network."""
        self._check_account_access()
        self._action_valid_add_account()
        return self._action_add_account()

    def _update_account(self):
        """Refresh the account data, implemented by each connector."""

    def update_account(self):
        """Refresh the account data according to the wizard selection."""
        self._check_account_access()
        try:
            return self._update_account()
        except Exception as ex:
            raise UserError(
                _(
                    "ERROR UPDATE ACCOUNT %(account)s: %(error)s",
                    account=self.account_id.name,
                    error=ex,
                )
            ) from ex
