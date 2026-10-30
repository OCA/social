# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError


class LinkedinRequestRejectedError(UserError):
    """LinkedIn refused the request itself, with a 4xx status.

    Told apart from the other failures of a request because it is the only one
    that says something about what was asked: a publication deleted on
    LinkedIn makes it refuse the whole batch of figures it belongs to, while a
    ``5xx`` or a timeout says nothing about any of them.
    """

    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code
