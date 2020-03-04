If you're using a multi-database installation (with or without dbfilter option)
where /web/databse/selector returns a list of more than one database, then
you need to add ``mail_tracking`` addon to wide load addons list
(by default, only ``web`` addon), setting ``--load`` option.
For example, ``--load=web,mail_tracking``
