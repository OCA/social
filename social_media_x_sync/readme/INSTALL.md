This module is installed on its own as soon as *Social Media Sync* and *Social
Media X* are both present, which is what a bridge module is for: the choice to
synchronize was already made by whoever installed *Social Media Sync*, and
this only keeps an X account from being left without the half that belongs to
it.

Installing *Social Media X* alone is a valid installation: the account is
linked, publishes and deletes, reads back the figures of the publications of
the last 30 days, and marks as *Deleted* the publication that is opened after
being deleted on X.

It adds no Python dependency of its own: it asks the connector for the tweepy
client and never builds one.
