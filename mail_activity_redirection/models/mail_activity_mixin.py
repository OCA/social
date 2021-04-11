# Copyright 2021 DEC SARL, Inc - All Rights Reserved.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models

import logging

_logger = logging.getLogger(__name__)


class MailActivityMixin(models.AbstractModel):
    _inherit = 'mail.activity.mixin'

    def activity_schedule(
        self,
        act_type_xmlid='',
        date_deadline=None,
        summary='',
        note='',
        **act_values
    ):
        """ Compare values used to create a new activity with the ones in
            mail activity redirection rules. If a match is set then
            assign a different user to this activity.
        """
        _logger.debug('activity_schedule')
        mail_activity_redirection = False
        redirections = self.env['mail.activity.redirection'].search([])
        if isinstance(note, bytes):
            note = note.decode('utf-8')
        for redirection in redirections:
            if redirection.user_id and redirection.match(
                self._name,
                act_type_xmlid,
                act_values.get('user_id'),
                act_values.get('stored_views_or_xmlid'),
                note,
            ):
                # Replace User with the one set in redirection rule
                act_values['user_id'] = redirection.user_id.id
                # Keep a reference on this redirection to assign created
                # activities
                mail_activity_redirection = redirection
                # Stop after first match
                break
        activity_ids = super().activity_schedule(
            act_type_xmlid, date_deadline, summary, note, **act_values
        )
        # activity_schedule can return False
        if activity_ids:
            activity_ids._link_to_mail_activity_redirection(
                mail_activity_redirection
            )
        return activity_ids

    def activity_schedule_with_view(
        self,
        act_type_xmlid='',
        date_deadline=None,
        summary='',
        views_or_xmlid='',
        render_context=None,
        **act_values
    ):
        """ Basic hook to keep a value of the original xmlid before its use
            for rendering.
        """
        _logger.debug('activity_schedule_with_view')
        # Store views_or_xmlid for possible use in activity_schedule
        act_values['stored_views_or_xmlid'] = views_or_xmlid
        return super().activity_schedule_with_view(
            act_type_xmlid, date_deadline, summary, views_or_xmlid,
            render_context, **act_values
        )
