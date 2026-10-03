This module is installed on its own as soon as *Social Media Sync* and *Social
Media Linkedin* are both present, which is what a bridge module is for: the
choice to synchronize was already made by whoever installed *Social Media
Sync*, and this only keeps a LinkedIn page from being left without the half
that belongs to it.

Installing *Social Media Linkedin* alone is a valid installation: the account
is linked, publishes, deletes and shows the daily figures of its page.

The mark the update check compares against
---------------

`social.account.linkedin_statistics_checkpoint` is stored by this module and
holds the daily figures LinkedIn reported for the whole page as of the last
import. An account that has no mark yet is given one on the first pass of
the bihourly check and announced as having nothing to import, so installing
this module on a database that already publishes on LinkedIn does not put
the notice up on every account at once.
