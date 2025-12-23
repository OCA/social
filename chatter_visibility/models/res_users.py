from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    chatter_visibility = fields.Selection(
        [
            ("hide", "Hide"),
            ("show", "Show"),
        ],
        string="Default Chatter Visibility",
        default="show",
        help=(
            "Select the default visibility of the chatter for this user.\n"
            "- *Hide*: The chatter will be collapsed by default.\n"
            "- *Show*: The chatter will be expanded by default."
        ),
    )

    @property
    def SELF_READABLE_FIELDS(self):
        # Include 'chatter_visibility' in fields readable by the user itself.
        return super().SELF_READABLE_FIELDS + ["chatter_visibility"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        # Include 'chatter_visibility' in fields writable by the user itself.
        return super().SELF_WRITEABLE_FIELDS + ["chatter_visibility"]

    @api.model
    def get_chatter_visibility(self):
        """
        Return whether the chatter should be shown for the current user.
        """
        return {"show_chatter": self.env.user.chatter_visibility != "hide"}
