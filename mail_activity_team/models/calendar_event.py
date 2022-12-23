# Copyright 2019 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def _get_default_team_id(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        domain = [("member_ids", "in", [user_id])]
        res_model = self.env.context.get("default_res_model")
        if res_model:
            model = self.env["ir.model"].search([("model", "=", res_model)], limit=1)
            domain.extend(
                ["|", ("res_model_ids", "=", False), ("res_model_ids", "in", model.ids)]
            )
        return self.env["mail.activity.team"].search(domain, limit=1)

    privacy = fields.Selection(
        selection_add=[("team", "Only team")],
        ondelete={"team": "set default"},
    )
    team_id = fields.Many2one(
        comodel_name="mail.activity.team",
        default=lambda s: s._get_default_team_id(),
    )

    @api.model
    def _get_read_fields(self, fields):
        # Always read these fields even if they were not wanted
        # as they are necessary to apply privacy on results
        expected_fields = ["privacy", "team_id"]
        extra_fields = []
        public_fields = self._get_public_fields()
        if not fields:
            fields = list(self._fields)
        for field in expected_fields:
            if field not in fields:
                fields.append(field)
                extra_fields.append(field)
        return fields, extra_fields, public_fields

    def read(self, fields=None, load="_classic_read"):
        # This function manages which fields a user can read based on the
        # team it belongs.
        fields, extra_fields, public_fields = self._get_read_fields(fields)
        result = super().read(fields, load)
        for r in result:
            # Apply filtering based on event privacy settings like it is
            # done in odoo.addons.calendar.models.calendar_event._read()
            if r["team_id"] and r["privacy"] == "team":
                team_id = r["team_id"]
                if isinstance(team_id, tuple):
                    team_id = team_id[0]
                team = self.env["mail.activity.team"].browse(team_id)
                if self.env.user not in team.member_ids:
                    for f in r:
                        if f not in public_fields:
                            if isinstance(r[f], list):
                                r[f] = []
                            else:
                                r[f] = False
                        if f in ("name", "display_name"):
                            r[f] = _("Busy")
            # Cleanup read results by removing fields that were expected
            # but not initially wanted
            for f in extra_fields:
                if f in r:
                    del r[f]
        return result
