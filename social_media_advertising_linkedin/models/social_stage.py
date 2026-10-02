# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class SocialStage(models.Model):
    _inherit = "social.stage"

    def _require_linkedin_stage(self, applies_to, code):
        """Return the LinkedIn stage of a scope and code, or explain its absence.

        Every write on LinkedIn stores back the status it leaves the record
        in, so the four of them need the stage to exist. The stages are
        module data declared ``noupdate``, which is why a missing one is
        reported the same way everywhere instead of being created on the fly:
        a stage created here would come back without its name, its level nor
        its sequence.

        :param applies_to: ``campaign``, ``group`` or ``ad``.
        :param code: status value as returned by LinkedIn.
        :rtype: recordset
        :raise UserError: when the stage is not installed.
        """
        stage = self._get_stage("linkedin", applies_to, code)
        if not stage:
            scopes = dict(self._fields["applies_to"]._description_selection(self.env))
            raise UserError(
                _(
                    "The LinkedIn stage with code %(code)s for %(scope)s is "
                    "missing. The LinkedIn stages are module data declared "
                    "noupdate: upgrading social_media_advertising_linkedin "
                    "recreates a deleted stage, but a stage whose code was "
                    "modified has to be restored by hand.",
                    code=code,
                    scope=scopes.get(applies_to, applies_to),
                )
            )
        return stage
