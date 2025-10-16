After installing the mail_thread_cc_bcc module, no additional configuration is required.
Whenever an email is received by Odoo—whether via template alias, forwarding, or SMTP integration—the system automatically includes recipients from the CC and BCC (Bcc) fields when processing the mail.thread.
This ensures that:
Messages sent with a copy or blind carbon copy are also routed correctly.
All relevant participants are associated with the corresponding thread or record.
This behavior is completely transparent and integrated into Odoo's standard email flow.