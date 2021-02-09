# -*- coding: utf-8 -*-
# Copyright 2016-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models
import logging

_logger = logging.getLogger(__name__)

try:
    from sendgrid.helpers.mail import TrackingSettings, SubscriptionTracking
except ImportError:
    _logger.info("ImportError raised while loading module.")
    _logger.debug("ImportError details:", exc_info=True)


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _prepare_sendgrid_tracking(self):
        track_vals = super(MailMail, self)._prepare_sendgrid_tracking()
        track_vals.update({
            'mail_id_int': self.id,
            'mass_mailing_id': self.mailing_id.id,
            'mail_stats_id': self.statistics_ids[:1].id
            if self.statistics_ids else False
        })
        return track_vals

    def _track_sendgrid_emails(self):
        """ Push tracking_email in mass_mail_statistic """
        tracking_emails = super(MailMail, self)._track_sendgrid_emails()
        for tracking in tracking_emails.filtered('mail_stats_id'):
            tracking.mail_stats_id.mail_tracking_id = tracking.id
        return tracking_emails

    def _prepare_sendgrid_data(self):
        """
        Add unsubscribe options in mass mailings
        :return: Sendgrid Email
        """
        s_mail = super(MailMail, self)._prepare_sendgrid_data()
        tracking_settings = TrackingSettings()
        if self.mailing_id.enable_unsubscribe:
            sub_settings = SubscriptionTracking(
                enable=True,
                text=self.mailing_id.unsubscribe_text,
                html=self.mailing_id.unsubscribe_text,
            )
            if self.mailing_id.unsubscribe_tag:
                sub_settings.substitution_tag = \
                    self.mailing_id.unsubscribe_tag
            tracking_settings.subscription_tracking = sub_settings
        else:
            tracking_settings.subscription_tracking = SubscriptionTracking(
                enable=False)

        s_mail.tracking_settings = tracking_settings
        return s_mail
