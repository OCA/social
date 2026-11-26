By default, this module changes the behavior of the native
``auto_delete`` flag:

* When ``auto_delete`` is enabled, the email record is kept after sending.
* For non-notification emails, the content (``body`` and ``body_html``)
  is cleared.
* When ``auto_delete`` is disabled, the email is kept without modifying
  its content.

To keep the email content even when ``auto_delete`` is enabled, set the
following system parameter:

* ``mail_partial_autodelete_debugmode`` = ``1``