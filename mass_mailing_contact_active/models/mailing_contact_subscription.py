# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import fields, models


class MailingContactSubscription(models.Model):

    _inherit = "mailing.contact.subscription"

    active = fields.Boolean(default=True)

    def init(self):
        """Add default value in DB for active column.

        Model mailing.contact.subscription is persisted using database table
        mailing_contact_list_rel.
        This model is used for following O2m fields:
        - mailing.list.subscription_ids
        - mailing.contact.subscription_list_ids

        However it is also used to materialize a M2m relation on following fields:
        - mailing.list.contact_ids
        - mailing.contact.list_ids

        If records are added using O2m fields, the ORM will properly get the default
        value defined for the active field before inserting in the table.
        However, if records are added using M2m fields, the ORM will only use the foreign
        keys to insert since it's an associative table.

        By defining a TRUE value as default for active field, we ensure the records
        added using the M2m fields will be active by default.
        """
        super().init()
        self.env.cr.execute(
            """ALTER TABLE ONLY mailing_contact_list_rel ALTER COLUMN active SET DEFAULT TRUE;"""  # noqa
        )
