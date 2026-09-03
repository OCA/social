The synchronization connectors
---------------

This module carries no call to any social media in particular. The connectors
that implement them — a *Social Media Sync Linkedin* and a *Social Media Sync
X* — are not written yet, so on its own it imports nothing. Until they exist,
*Social Media Linkedin* and *Social Media X* still hold both halves and do not
install alongside this module.

`actor_urn`
---------------

`social.post.account.actor_urn` has no reader, neither in *Social Media Base*
nor in any connector. It looks like it belongs to the reactions, which take
the actor performing them as an argument, but nothing fills it and nothing
reads it. It was left in place rather than removed with the rest, and it is
the kind of field a synchronization connector either starts using or the
family drops.
