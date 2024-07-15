For having discrete unsubscriptions from other recipients than the mailing lists, you
need to add a glue module that adds two fields in the associated model:

- `opt_out`.
- Either `email` or `email_from`.

See `mass_mailing_custom_unsubscribe_event` for an example.
