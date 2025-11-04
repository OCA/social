# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


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

    def _get_csrf_state_token(self):
        pass

    def _compute_csrf_state_token(self):
        for media in self:
            media.csrf_state_token = media._get_csrf_state_token()

    def _get_url_redirect(self):
        pass

    def _action_add_account(self):
        """
        Social media modules that inherit from this one should
        override this method as needed; the method is intended
        to redirect to the social network authorization.
        """
        pass

    def _action_valid_add_account(self):
        return True

    def action_associate_social_account(self):
        self._action_valid_add_account()
        return self._action_add_account()

    def _update_account(self):
        pass

    def update_account(self):
        return self._update_account()
