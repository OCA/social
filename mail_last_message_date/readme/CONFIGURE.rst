#. Inherit ``mail.last.message.date.mixin`` on the models to track
   (alongside ``mail.thread`` if the model does not already inherit it).
#. (Optional) override ``_get_tracked_message_types()`` on the model to return a list of
   ``message_types``. If no ``message_types`` are returned, any message updates
   ``last_message_date``.
#. Example:

   .. code-block:: python

      from odoo import models

      class PurchaseOrder(models.Model):
          _inherit = ["purchase.order", "mail.last.message.date.mixin"]

          def _get_tracked_message_types(self):
              return ["email"]
