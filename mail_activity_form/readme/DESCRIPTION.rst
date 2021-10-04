This module allows you to provide some markup in the ``default_description``
field of ``mail.activity.type``, which makes some portions of the ``note``
field of resulting ``mail.activity`` records editable and others computed.

With this, you can implement form based workflows where you have to fill in
certain forms at certain times, and have to prove later what you filled in
when as mail activities, while still being able to access the data filled
in programmatically afterwards.
