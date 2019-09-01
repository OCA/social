When you click on *Send a message* in the Open Chatter,
Odoo displays the Message Composer:

|composer|

.. |composer| image:: composer.png
   :alt: Message Composer

You may notice that it adds suggestions of recipients:
here *Ready Mat (ready.mat28@example.com)*

These suggestions can be useful, but having them checked by default
is dangerous: for example a user could mistakenly send
a sensitive internal message to a customer.

The purpose of this module is to make sure that these suggestions
are not checked by default.
