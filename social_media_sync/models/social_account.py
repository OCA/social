# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta

from odoo import Command, _, api, fields, models

_logger = logging.getLogger(__name__)

# How long the initial sync waits before trying again an account another
# transaction was updating. Long enough for the update that took the row to
# be over, short enough for the dashboard not to announce an import that is
# not running.
INITIAL_SYNC_RETRY_DELAY_MINUTES = 5

# How long the import waits after being asked for. The association that asks
# for it is still writing the account when it does, so a cron starting right
# away reads the row from before that write and loses the race against it.
INITIAL_SYNC_TRIGGER_DELAY_SECONDS = 15


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
        help="The account was just associated and its posts still have to be "
        "imported by the initial sync cron.",
    )
    posts_need_import = fields.Boolean(
        default=False,
        copy=False,
        help="The periodic check found publications on the social media that "
        "Odoo has not imported yet.",
    )

    def _update_posts_statistics(self, post_id, domain, imported=None):
        """Update the posts and their statistics.

        The figures answered here are read back from what is stored, so they
        come out the same whether the social media was read or the call was
        skipped: a quota window still open, a refusal the connector swallowed
        to keep the other accounts going. ``imported`` is what tells the two
        apart, and the caller needs it to know whether the first import of an
        account really happened.

        :param post_id: post to update, all of them when not set.
        :param domain: additional domain on the posts.
        :param imported: set the connectors add the id of every account they
            actually read to. An account missing from it was not imported.
        :rtype: list
        """
        return []

    def _report_imported(self, imported):
        """Note that these accounts were really read by the import.

        The counterpart of the ``imported`` accumulator of
        :meth:`_update_posts_statistics`: the connectors call it at the point
        where the social media has already answered, so an account they
        skipped or rolled back never gets in.

        :param imported: the accumulator, ``None`` when the caller does not
            care which accounts were read.
        """
        if imported is not None:
            imported.update(self.ids)

    def _detects_pending_posts(self):
        """Whether the social media can say that this account has posts to import.

        Not every API can. The only endpoint of X that knows whether the
        timeline moved is the one that reads it, and reading it *is* the
        import, so its connector answers ``False`` here and its accounts are
        imported on every pass instead of announcing anything first.

        This is what keeps :meth:`_accounts_to_import` from dropping those
        accounts for good: a filter on ``posts_need_import`` alone would skip
        forever the very accounts that can never carry it.

        :rtype: bool
        """
        self.ensure_one()
        return False

    def _accounts_to_import(self):
        """Narrow these accounts down to the ones worth importing.

        The import is the call whose cost grows with the history of the
        account, which is the whole reason this module exists; spending it on
        an account nothing moved on is what that line was cut to avoid. The
        daily figures are refreshed on every account regardless: they cost a
        fixed number of calls and they move without anything being published.

        An account whose connector cannot detect changes is kept, always. One
        whose connector can is kept when something says it is behind:
        ``posts_need_import``, or a first import that never ran.
        ``pending_initial_sync`` is not decorative here — a freshly associated
        account has been through no check, and without it the button could not
        unblock an initial sync that failed, which is a job it has.

        :rtype: recordset
        """
        return self.filtered(
            lambda account: not account._detects_pending_posts()
            or account.posts_need_import
            or account.pending_initial_sync
        )

    def update_posts_statistics(self, post_id=None, domain=None):
        """Refresh the posts and the statistics of the accounts.

        An account read here does not need its initial sync any more: this is
        the very import the cron was going to run, so the flag is cleared and
        the dashboard stops announcing a background import. It is also what
        keeps the *Update* button able to unblock an account whose import
        failed.

        Only the accounts the connectors report as read are cleared. An
        import the quota stopped brings nothing in, and clearing the flag for
        it would tell the dashboard about posts that are not there and take
        the account out of the monthly import for good.

        ``posts_need_import`` is taken down on the same terms and for the same
        reason: the import is the only thing that resolves it. A connector
        clearing it itself, as the LinkedIn one does at the point where the
        feed answered, leaves nothing for this pass to do; the pass is what
        covers the ones that do not.

        Asked for every account, only the ones :meth:`_accounts_to_import`
        keeps are read. Asked for a given account, that account is read
        whatever its flags say: the user pressing *Update* on one card has
        already said which one he wants, and the narrowing is only there to
        save the calls nobody asked for.

        An empty recordset is every account as far as the connectors are
        concerned, so a narrowing that keeps nothing has to stop here instead
        of handing them one. The empty answer is what the dashboard reads to
        tell that run from one that really imported something, and word the
        button accordingly.

        :param post_id: post to update, all of them when not set.
        :param domain: additional domain on the posts.
        :rtype: list
        """
        accounts = self or self.search([])
        if not self:
            accounts = accounts._accounts_to_import()
            if not accounts:
                return []
        imported = set()
        statistics = accounts._update_posts_statistics(post_id, domain, imported)
        imported_accounts = accounts.filtered(lambda account: account.id in imported)
        pending = imported_accounts.filtered("pending_initial_sync")
        if pending:
            pending.sudo().write({"pending_initial_sync": False})
        # ``_clear_posts_need_import`` keeps the ones actually flagged.
        imported_accounts._clear_posts_need_import()
        return statistics

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
            with account._account_guard("Error on the full resync of the account %s"):
                account._full_resync()

    def _trigger_initial_sync(self):
        """Run the posts-statistics sync now so the dashboard is populated
        right after linking an account.

        Called on the accounts that were just associated: they are flagged so
        the cron only syncs them and not every account of every user.

        The cron is asked for a moment ahead instead of for right now. The
        caller is in the middle of the association, which writes the very row
        the import writes its statistics on, and a cron woken inside that
        transaction starts on a snapshot older than its commit: it reaches the
        account, loses the race and leaves the dashboard announcing an import
        that only the retry a few minutes later brings in.
        """
        if not self:
            return
        self.sudo().write({"pending_initial_sync": True})
        cron = self.env.ref("social_media_sync.initial_sync_account_job")
        cron.sudo()._trigger(
            at=fields.Datetime.now()
            + timedelta(seconds=INITIAL_SYNC_TRIGGER_DELAY_SECONDS)
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
            + timedelta(minutes=INITIAL_SYNC_RETRY_DELAY_MINUTES)
        )

    def _close_initial_sync(self, error=None):
        """Tell the user how the import went, and close a failed one.

        The dashboard shows the account as syncing while the flag is set. An
        import that failed clears it here, with the reason left on the
        account, because nothing is going to retry it on its own: the bus
        notification of the connectors reaches nobody when the cron runs, and
        the user imports again with the *Update* button.

        An import that worked has already cleared the flag itself, in
        :meth:`update_posts_statistics`, and one the connector skipped has
        deliberately kept it: nothing was read, so the account still needs its
        first import and the caller asks the cron to come back for it.

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
            # An account still pending was skipped, not imported: the quota of
            # the social media was spent, or the connector had nothing to read
            # it with. The flag also keeps the bihourly check away from it, so
            # leaving it to the monthly cron would freeze the account until
            # then.
            if account.pending_initial_sync:
                postponed |= account
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
            account._notify_user_client(
                target=account.user_id.partner_id,
                notif_type="social_form_info",
                notif_message=_("The posts of the account were updated."),
                media=account.media_type or account.media_id.name,
                account_name=account.name,
                # The dashboard reloads itself on this type, so it is not the
                # notification service reading it, and the account is what
                # tells the card which figures to read again.
                bus_type="social_posts_updated",
                payload={"account_id": account.id},
            )

    def _flag_posts_need_import(self):
        """Record that these accounts have publications waiting to be imported.

        The counterpart of :meth:`~.social.account._flag_credentials_expired`
        for the other thing the dashboard has to announce. The two states are
        separate: an account whose token works can still be behind its social
        media, and one with nothing to import can still need a new
        authorization.

        An account already flagged is left alone. Its row is the one the
        import writes on, and the dashboard is already drawing the notice, so
        writing it again only pushes the same message a second time.
        """
        pending = self.filtered(lambda account: not account.posts_need_import)
        if not pending:
            return
        pending.sudo().write({"posts_need_import": True})
        pending._notify_posts_need_import()

    def _clear_posts_need_import(self):
        """Take down the notice the pending publications put on the dashboard.

        The import that brings them in is what resolves the state, and the bus
        message is what makes the notice go away without the user reloading
        the page.
        """
        flagged = self.filtered("posts_need_import")
        if not flagged:
            return
        flagged.sudo().write({"posts_need_import": False})
        flagged._notify_posts_need_import(need_update=False)

    def _notify_posts_need_import(self, need_update=True):
        """Tell each user which of his accounts have publications to import.

        The check that finds them runs in a cron, whose user is not the one
        owning the account, so the message has to be addressed to each
        responsible user. The payload names the accounts because the dashboard
        has to tell the user which one is behind: somebody responsible for
        four accounts can do nothing with a notice that only says *something
        has to be imported*. Each partner is told about his own accounts and
        about no others.

        Its own bus type, and not the one the expired credentials use, is what
        keeps the two notices apart: neither state implies the other and both
        can be drawn at once on the same card.

        :param need_update: whether the notice goes up or comes down.
        """
        self._notify_accounts_by_partner("social_posts_need_import", need_update)

    @api.model
    def _import_command(self, post_account, values, attachments, media_refs):
        """Return the command that writes one imported publication.

        The medias go in the same write as the rest of the publication, so a
        downloaded media is never stored without the reference telling it
        apart from one attached in Odoo. The references already stored win
        nothing over the new ones: what this pass read is what the social
        media says today.

        :param post_account: the line already in Odoo, an empty recordset when
            the publication has never been imported.
        :param values: the fields read from the social media.
        :param attachments: the medias downloaded in this pass.
        :param media_refs: the reference of each downloaded media, keyed by
            its identifier.
        :rtype: tuple
        """
        if attachments:
            values = {
                **values,
                "image_ids": [
                    Command.link(attachment.id) for attachment in attachments
                ],
                "media_refs": {**(post_account.media_refs or {}), **media_refs},
            }
        if not post_account:
            return Command.create(values)
        return Command.update(post_account.id, values)

    def _accounts_of_media(self, media_type):
        """Return the accounts of one social media this pass has to read.

        The feed is read one account at a time and the quota is spent per
        account, so a recordset holding accounts of more than one social media
        is narrowed instead of taken whole: the others are not this
        connector's to read. An empty recordset means *every account*, which
        is how the crons call it.

        :param media_type: the social media the caller reads.
        :rtype: recordset
        """
        if not self:
            return self.search([("media_type", "=", media_type)])
        return self.filtered(lambda account: account.media_type == media_type)

    def _media_statistics_payload(self, media_type, statistics, extra_fields=()):
        """Append the figures of one social media to what the others answered.

        Each connector adds its own accounts to the payload the dashboard
        reads, so the chain of ``super()`` calls ends with the accounts of
        every social media in the order the connectors ran.

        :param media_type: the social media whose accounts are added.
        :param statistics: what the connectors before this one answered.
        :param extra_fields: the fields this social media reads on top of the
            common ones, in the place they occupy in the payload.
        :rtype: list
        """
        return list(statistics or []) + self.search_read(
            [("media_type", "=", media_type)],
            [
                "name",
                "company_id",
                "media_id",
                *extra_fields,
                "impression_count",
                "interactions_count",
                "engagement",
                "need_update",
            ],
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
