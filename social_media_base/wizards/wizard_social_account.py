# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class WizardSocialAccount(models.TransientModel):
    """Associate an account of a social media with the database.

    Each connector inherits this wizard to ask for the credentials its own
    social media needs and to run its association flow; the generic part
    only holds what all of them share.
    """

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
    update_token = fields.Boolean(
        default=False,
        help="Only enable this field if the access token has expired and has "
        "to be requested again",
    )
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

    def _set_csrf_state_token(self):
        """Store the anti-CSRF state token of the OAuth flow."""
        for media in self:
            media.csrf_state_token = media._get_csrf_state_token()

    def _get_url_redirect(self):
        """Return the OAuth callback URL, implemented by each connector."""

    def _action_add_account(self):
        """Redirect to the authorization page of the social media.

        Connector modules override it and keep the state token computed
        here to exchange the credentials and the access token.
        """
        self._set_csrf_state_token()

    def _action_valid_add_account(self):
        """Validate the wizard before requesting access to the social media."""
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
        """Link the account with the social media."""
        self._check_account_access()
        self._action_valid_add_account()
        return self._action_add_account()

    def _update_account(self):
        """Refresh the account data, implemented by each connector."""

    def action_update_account(self):
        """Refresh the account data according to the wizard selection."""
        self._check_account_access()
        try:
            result = self._update_account()
        except (AccessError, UserError, ValidationError):
            # Already meant for the user, wrapping them would hide their type.
            raise
        except Exception as ex:  # noqa: BLE001 - the API may fail in any way
            raise UserError(
                _(
                    "The account %(account)s could not be updated: %(error)s",
                    account=self.account_id.name,
                    error=ex,
                )
            ) from ex
        # The credentials just proved they work, so the warning the expired
        # ones left on the dashboard is no longer true. It is taken down here
        # and not inside ``_update_account`` because that one is a connector
        # hook: a new connector cannot forget to do it if it never had to.
        self.account_id._clear_credentials_flag()
        return result
