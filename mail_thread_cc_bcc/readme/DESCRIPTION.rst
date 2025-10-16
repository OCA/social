This module extends the default behavior of mail.thread to include <b>CC</b> and <b>BCC</b> recipients in the routing process for incoming email messages.
With it, messages arriving in Odoo via the email gateway now also consider the addresses added as copies and blind carbon copies, ensuring that all relevant recipients are processed appropriately.
Main features:
Automatic inclusion of CC and BCC addresses in message_dict['recipients'].
Fully compatible with Odoo's native message routing flow.
Lightweight implementation with no impact on existing functionality.