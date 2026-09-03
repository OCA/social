# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging

import psycopg2
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY

_logger = logging.getLogger(__name__)

# How long the initial sync waits before trying again an account another
# transaction was updating. Long enough for the update that took the row to
# be over, short enough for the dashboard not to announce an import that is
# not running.
INITIAL_SYNC_RETRY_DELAY_MINUTES = 5


class SocialAccount(models.Model):
    """Everything the account reads back from its social media.

    Publishing costs a fixed number of calls per account, however much the
    account has published; reading back what it already published does not.
    That is the line this module is cut along, and it is why all of this is
    here and not in ``social_media_base``.
    """

    _inherit = "social.account"

    pending_initial_sync = fields.Boolean(
        default=False,
        copy=False,
        help="Technical field: the account was just associated and its posts "
        "still have to be imported by the initial sync cron.",
    )

    def _filter_statistics(self, entity_statistics):
        """Add up the statistics a connector reports for several entities.

        The connector is the one building ``entity_statistics``, so the tuple
        is the contract between both sides: six numbers, always in the order
        ``(clicks, likes, comments, shares, engagement, impressions)``, the
        same one the rows of ``social.account.statistics`` are written from.

        :param dict entity_statistics: statistics tuple by entity key.
        :return: the totals, keyed by the field they feed.
        :rtype: dict
        """
        post_statistics = {
            "click_count": 0,
            "like_count": 0,
            "comment_count": 0,
            "share_count": 0,
            "engagement": 0,
            "impression_count": 0,
        }
        for __, statistics in entity_statistics.items():
            post_statistics["click_count"] += statistics[0]
            post_statistics["like_count"] += statistics[1]
            post_statistics["comment_count"] += statistics[2]
            post_statistics["share_count"] += statistics[3]
            post_statistics["engagement"] += statistics[4]
            post_statistics["impression_count"] += statistics[5]
        return post_statistics

    def _update_posts_statistics(self, post_id, domain):
        """Update the posts and their statistics.

        :param post_id: post to update, all of them when not set.
        :param domain: additional domain on the posts.
        :rtype: list
        """
        return []

    def update_posts_statistics(self, post_id=None, domain=None):
        """Refresh the posts and the statistics of the accounts.

        An account refreshed here does not need its initial sync any more:
        this is the very import the cron was going to run, so the flag is
        cleared and the dashboard stops announcing a background import. It is
        also what keeps the *Update* button able to unblock an account whose
        import failed.

        :param post_id: post to update, all of them when not set.
        :param domain: additional domain on the posts.
        :rtype: str
        """
        accounts = self or self.search([])
        statistics = self._update_posts_statistics(post_id, domain)
        pending = accounts.filtered("pending_initial_sync")
        if pending:
            pending.sudo().write({"pending_initial_sync": False})
        return json.dumps(statistics)

    def _backfill_statistics(self):
        """Write the time series as far back as the social media answers.

        Empty hook, the counterpart of :meth:`_snapshot_statistics` for an
        account that was just associated: the range is not decided here
        because it is the API of each social media that decides how far back
        it reports figures by day.

        :rtype: None
        """
        return

    def _full_resync(self):
        """Hook for the connectors to read everything again and reconcile it.

        The ordinary refresh is free to ask the social media only about what it
        needs, which on a large account is what keeps it affordable. What it
        cannot do that way is notice that a publication was **deleted** on the
        social media: nothing is left to ask about. This is the pass that reads
        the whole thing and reconciles it.

        The default is the ordinary refresh: a social media with no notion of a
        feed read whole has nothing extra to do here, and a connector that
        already imports incrementally keeps its own way of doing it.

        Nothing is done without accounts: a connector delegates here the
        accounts it does not handle, and :meth:`update_posts_statistics` takes
        an empty recordset as every account, which would refresh a second time
        the very accounts the connector already reconciled.
        """
        if not self:
            return None
        return self.update_posts_statistics()

    def action_full_resync(self):
        """Read everything again from the social media, from the account form."""
        self.ensure_one()
        self._full_resync()

    @api.model
    def _run_full_resync(self):
        """Reconcile every account against its social media.

        This is what notices the publications deleted on the social media, and
        the only thing that does: the ordinary refresh no longer reads whole
        feeds. It runs seldom on purpose, because reading everything costs one
        call per page of publications.

        Each account is reconciled in its own savepoint: the pass writes as it
        goes, so a failure on one account must not undo what the previous ones
        already imported nor stop the ones still to come.

        The cron record does not set a user, so the search needs ``sudo()`` to
        reach the accounts of every responsible, like :meth:`_run_full_resync`'s
        sibling crons do. The accounts waiting for their initial sync are left
        out: that import is this very pass, and the two would fight over the
        same rows.
        """
        for account in self.sudo().search([("pending_initial_sync", "=", False)]):
            try:
                with self.env.cr.savepoint():
                    account._full_resync()
            except psycopg2.OperationalError as error:
                if error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    raise
                _logger.exception(
                    "Error on the full resync of the account %s", account.id
                )
            except Exception:  # noqa: BLE001 - one account must not stop the rest
                _logger.exception(
                    "Error on the full resync of the account %s", account.id
                )

    def _trigger_initial_sync(self):
        """Run the posts-statistics sync now so the dashboard is populated
        right after linking an account.

        Called on the accounts that were just associated: they are flagged so
        the cron only syncs them and not every account of every user.
        """
        if not self:
            return
        self.sudo().write({"pending_initial_sync": True})
        cron = self.env.ref("social_media_sync.initial_sync_account_job")
        cron.sudo()._trigger()

    @api.model
    def _is_concurrency_error(self, error):
        """Whether the error is the one PostgreSQL raises on a lost race.

        :param error: the exception to look at.
        :rtype: bool
        """
        return (
            isinstance(error, psycopg2.OperationalError)
            and error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY
        )

    def _reschedule_initial_sync(self):
        """Ask the cron to import these accounts again in a few minutes.

        The cron only runs once a month, and the retry Odoo does on a
        concurrency error covers the web requests, not the crons
        (:meth:`~odoo.addons.base.models.ir_cron.ir_cron._callback` only logs
        and rolls back): an account left pending because another transaction
        was writing its row would keep the dashboard waiting for an import
        nobody was going to run again.
        """
        if not self:
            return
        cron = self.env.ref(
            "social_media_sync.initial_sync_account_job", raise_if_not_found=False
        )
        if not cron:
            return
        _logger.info(
            "The initial sync of the accounts %s is retried in %s minutes.",
            self.ids,
            INITIAL_SYNC_RETRY_DELAY_MINUTES,
        )
        cron.sudo()._trigger(
            at=fields.Datetime.now()
            + relativedelta(minutes=INITIAL_SYNC_RETRY_DELAY_MINUTES)
        )

    def _close_initial_sync(self, error=None):
        """Clear the pending flag and tell the user how the import went.

        The dashboard shows the account as syncing while the flag is set, so
        it is cleared whether the import worked or not, and the reason of a
        failure is left on the account: the bus notification of the connectors
        reaches nobody when the cron runs, and the user can import again with
        the *Update* button.

        :param error: the exception the import raised, if it did.
        """
        self.ensure_one()
        if error is not None:
            self._register_initial_sync_failure(error)
        self.pending_initial_sync = False
        self._notify_posts_updated()

    @api.model
    def _run_initial_sync(self):
        """Import the posts of the accounts that were just associated.

        Each account is synced in its own savepoint: a failure on one of them
        must not lose what the previous ones already imported. This is also
        where the time series of the account is filled backwards, as far as
        the social media answers, so the graph view has a past to draw.

        An account whose row another transaction wrote first is not fought
        over. Its flag is kept and the cron is asked to come back in a few
        minutes, because the write that lost the race is the whole import:
        clearing the flag would leave the dashboard announcing posts that were
        never brought in. Unlike a web request, a cron gets no retry of its
        own, so the concurrency error is handled here instead of raised.

        The cron record does not set a user, so the search needs ``sudo()``
        to reach the pending accounts of every responsible, like
        :meth:`_run_check_media_updates` does.
        """
        pending = self.sudo().search([("pending_initial_sync", "=", True)])
        postponed = self.browse()
        for account in pending:
            error = None
            try:
                with self.env.cr.savepoint():
                    account.update_posts_statistics()
                # The time series is filled in its own savepoint. It reaches
                # further back than the import and costs its own calls, so an
                # account whose history cannot be read keeps the publications
                # that were already imported instead of losing them too.
                with self.env.cr.savepoint():
                    account._backfill_statistics()
            except Exception as sync_error:  # noqa: BLE001 - one account cannot stop the rest
                if self._is_concurrency_error(sync_error):
                    _logger.info(
                        "The initial sync of the account %s lost a race "
                        "against another update, it is retried later.",
                        account.id,
                    )
                    postponed |= account
                    continue
                _logger.exception(
                    "Error on the initial sync of the account %s", account.id
                )
                error = sync_error
            account._close_initial_sync(error)
        postponed._reschedule_initial_sync()

    def _register_initial_sync_failure(self, error):
        """Tell the responsible user that the first import did not go through.

        The flag is cleared whatever happens, so nothing on the dashboard
        recalls the failure afterwards, and the cron that runs the import has
        nobody connected to receive a bus notification: the note on the
        account is the only durable trace the user in charge can find.

        :param error: the exception the import raised.
        """
        self.ensure_one()
        self.message_post(
            body=_(
                "The posts of the account could not be imported: %(error)s. "
                "Press the Update button of the dashboard to import them "
                "again.",
                error=error,
            ),
            partner_ids=self.user_id.partner_id.ids,
        )

    def _notify_posts_updated(self):
        """Tell the responsible user that the posts of the account changed.

        The initial sync runs in a cron, so the dashboard the user is looking
        at knows nothing about it: this is what makes it reload itself. The
        message names the account because a user may be responsible for
        several of them.
        """
        for account in self:
            self.env["bus.bus"]._sendone(
                account.user_id.partner_id,
                "social_posts_updated",
                {
                    "account_id": account.id,
                    "message_type": "info",
                    "message": account._format_user_notification(
                        _("The posts of the account were updated."),
                        media=account.media_type or account.media_id.name,
                        account_name=account.name,
                        message_type="info",
                    ),
                },
            )

    def _on_account_associated(self):
        """Queue the import of what these accounts already published."""
        result = super()._on_account_associated()
        self._trigger_initial_sync()
        return result

    def _get_check_media_updates_domain(self):
        """Leave out the accounts whose first import has not run yet.

        The check writes the same row the import writes its statistics on, and
        the two crons run in parallel threads, so a check landing on an account
        that is being imported is what aborts one of them with a serialization
        failure. Nothing is lost by waiting: the import brings in the very
        updates this check looks for.
        """
        return super()._get_check_media_updates_domain() + [
            ("pending_initial_sync", "=", False),
        ]
