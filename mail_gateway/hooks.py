def pre_init_hook(cr):
    """
    The objective of this hook is to speed up the installation
    of the module on an existing Odoo instance.

    Without this script, big databases can take a long time to install this
    module.
    """
    cr.execute(
        """ALTER TABLE mail_message
    ADD COLUMN gateway_channel_id int"""
    )
