Over the years of using an Odoo instance, its database can grow to a very large size.
Message from the chatter can quickly add up to this load and some of them have no added
value after their related records has been settled.

This module allows to configure mail message retention policies on a per model basis.
Go to Settings > Technical > Discuss > Message Purge to add some configuration.

A cron will run daily to purge old messages following the configurations. A maximum of
1000 messages by model will be delete by day to avoid blocking normal Odoo execution.
