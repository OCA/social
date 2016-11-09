
.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==============
Pinterest Social Media Icon Extension
==============

This module adds Pinterest social media icon. By default, the icon will
be shown on the footer, about us, and the Blog, like the original icons.



Configuration
=============

- Go in the backend under settings / website
- You can now also add your Pinterest Account


Usage
=====

- Normal social icons::

    <a t-att-href="website.social_facebook" t-if="website.social_facebook"><i class="fa fa-facebook-square"/></a>
    
    <a t-att-href="website.social_twitter" t-if="website.social_twitter"><i class="fa fa-twitter"/></a>
    
    <a t-att-href="website.social_linkedin" t-if="website.social_linkedin"><i class="fa fa-linkedin"/></a>
    
    <a t-att-href="website.social_youtube" t-if="website.social_youtube"><i class="fa fa-youtube-play"/></a>
    
    <a t-att-href="website.social_googleplus" t-if="website.social_googleplus"><i class="fa fa-google-plus-square"/></a>
    
    <a t-att-href="website.social_github" t-if="website.social_github"><i class="fa fa-github"/></a>

- The new social icons:

    <a t-att-href="website.social_pinterest" t-if="website.social_pinterest"><i class="fa fa-pinterest"/></a>

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/8.0


Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/social/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.


Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.
* Pinterest: `Brand guidelines <https://business.pinterest.com/en/brand-guidelines\#brand-basics>`_ `Icons <https://business.pinterest.com/sites/business/files/pinterest_badge.zip>`_.

Contributors
------------

* Pere Albujer (pedro.albujer.rico@diagram.es)

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
