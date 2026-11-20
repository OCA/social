# SPDX-FileCopyrightText: 2025 hugues de keyzer
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from odoo import fields, models

TRACK_OPEN_PARAMETER = "mailing.mailing.track_open"
TRACK_LINKS_PARAMETER = "mailing.mailing.track_links"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mailing_track_open = fields.Boolean(
        "Track Open", config_parameter=TRACK_OPEN_PARAMETER
    )
    mailing_track_links = fields.Boolean(
        "Track Link Clicks", config_parameter=TRACK_LINKS_PARAMETER
    )
