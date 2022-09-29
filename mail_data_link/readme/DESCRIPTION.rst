This technical module will make internal data links clickable in email
notifications.

Effectively, internal data links such as

.. code-block::

   <a href="#" data-oe-model="res.partner" data-oe-id="7">Test</a>

will be rewritten as

.. code-block::

   <a href="$BASE_URL/mail/view?model=res.partner&res_id=7">test</a>
