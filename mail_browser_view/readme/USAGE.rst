Upon module installation, a secure token will be generated for each mail,
allowing it to be reached *via* a constructed URL.
You can then put the following placeholder::

    <a href="#" class="view_in_browser_url">View this mail in browser</a>

anywhere in your mail templates (of course, the link text can be changed).
If you use templates not managed through Odoo editor, it is strongly advised
to use the `mail_inline_style` module so the styles do not get messed up.

Be aware that this feature will not work for templates
having "Auto-Delete" value set to `True`.
To avoid any unwanted 404 errors, all the placeholders within such templates
will be removed automatically in the generated mails.
