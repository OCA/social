Many Odoo modules retrieve system parameter information embedded in other
functions that make it difficult to adapt the place information is retrieved
from.

A point in case is the configuration of Client ID and Client Secret Value, where
both the fetchmail_outlook module and the microsoft_outlook module just assume
that an Odoo database can only be connected to one Microsoft profile, and therefore
have the information in a system parameter.

This module makes it possible to preset the value to be retrieved from a system
parameter in the context, making no assumptions of where the alternative values
will come from, allowing other modules to override the standard methods.

How to use
==========

Suppose there is some Odoo method that has retrieving system parameter information
without using an overridable function for this:

```
    def _compute_outlook_uri(self):
        Config = self.env['ir.config_parameter'].sudo()
        microsoft_outlook_client_id = Config.get_param("microsoft_outlook_client_id")
        ...
        for record in self:
           # More code
```

However we have multiple connections with each their own value for client id.

With help of this module we can do:

```
class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    microsoft_outlook_client_identifier = fields.Char(
        "Outlook Client Id",
        help="Specific client_id for this server",
    )
    .....
    def _compute_outlook_uri(self):
        self.ensure_one()
        preset_self = self.with_context(
            preset_microsoft_outlook_client_id=self.microsoft_outlook_client_identifier,
        )
        uri = super(IrMailServer, preset_self)._compute_outlook_uri()
        ....
```
