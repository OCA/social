# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import exceptions


class DetailsRequiredError(exceptions.ValidationError):
    pass


class ReasonRequiredError(exceptions.ValidationError):
    pass
