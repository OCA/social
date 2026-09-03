# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError


class SocialCredentialsError(UserError):
    """The social media refused the credentials of the account.

    Told apart from the other errors because it is the only failure worth
    retrying on the spot: refreshing the token may be all it takes for the
    same call to go through. Anything the social media refuses about the
    content itself is not going to change by trying again.
    """
