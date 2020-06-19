You can customize what reasons will be displayed to your unsubscriptors when
they are going to unsubscribe. To do it:

#. Go to *Email Marketing > Configuration > Unsubscription Reasons*.
#. Create / edit / remove / sort as usual.
#. If *Details required* is enabled, they will have to fill a text area to
   continue.

For having discrete unsubscriptions from other recipients than the mailing
lists, you need to add a glue module that adds 2 fields in the associated
model:

- `opt_out`.
- Either `email` or `email_from`.

See `mass_mailing_custom_unsubscribe_event` for an example.
