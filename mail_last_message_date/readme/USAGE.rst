Use *Last Message Date* in a filter, or as the trigger date of a timed automated
action, for example to act on records that have had no new message for 7 days.
Records without any counted message have no *Last Message Date*, so such an action
never acts on them.

To fix the message types for a model regardless of the system parameter, override
``_get_tracked_message_types()``:

.. code-block:: python

   from odoo import models

   class PurchaseOrder(models.Model):
       _inherit = "purchase.order"

       def _get_tracked_message_types(self):
           return ["email"]
