# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __openerp__.py
#
##############################################################################
from sendgrid.helpers.mail.mail import TrackingSettings, SubscriptionTracking
from openerp import models


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
                sub_settings.set_substitution_tag(
                    self.mailing_id.unsubscribe_tag)
            tracking_settings.set_subscription_tracking(sub_settings)
        else:
            tracking_settings.set_subscription_tracking(SubscriptionTracking(
                enable=False))

        s_mail.set_tracking_settings(tracking_settings)
        return s_mail
