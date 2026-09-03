This module depends on *Social Media Base* and is not installed with it: an
Odoo that only writes and publishes does not need it, and the whole point of
having it apart is not paying for what it does.

It brings nothing of its own for a social media in particular. A
synchronization connector is what implements the calls for one of them, the
same way *Social Media Linkedin* or *Social Media X* implement publishing.
Installed without one, the scheduled actions run, find nothing to ask anybody,
and leave everything as it is.
