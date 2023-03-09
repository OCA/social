You need to do nothing. The module is configured appropriately out of the box.

The mail queue processing is made by a cron job. This is normal Odoo behavior,
not specific to this module. However, since you will start using that queue for
every message posted by any user in any thread, this module configures that job
to execute every minute by default.

You can still change that cadence after installing the module (although it is
not recommended). To do so:

#. Log in with an administrator user.
#. Activate developer mode.
#. Go to *Settings > Technical > Automation > Scheduled Actions*.
#. Edit the action named "Mail: Email Queue Manager".
#. Lower down the frequency in the field *Execute Every*. Recommended: 1 minute.
