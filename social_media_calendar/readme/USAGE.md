Calendar view
-------------------

1. Go to Social Media > Posts
2. Click on the Calendar icon to open the calendar view
3. Click on a Post and a view with the post details will open.

Colors by publication status
---------------------------

The calendar view will show the posts in different colors depending on their publication status:

- Draft

  ![POST_DRAFT](../static/img/readme/POST_DRAFT.png)
- Planned

  ![POST_PLANNED](../static/img/readme/POST_PLANNED.png)
- Publishing

  ![POST_PUBLISHING](../static/img/readme/POST_PUBLISHING.png)
- Published

  ![POST_PUBLISHED](../static/img/readme/POST_PUBLISHED.png)
- Cancelled

  ![POST_CANCELLED](../static/img/readme/POST_CANCELLED.png)

- Calendar view by color

  ![POSTS_CALENDAR](../static/img/readme/POSTS_CALENDAR.png)

Uninstalling the module
-----------------------

The calendar view is added to the posts action of *Social Media Base*, which
belongs to another module and is therefore not reverted by Odoo on uninstall.
Uninstalling *Social Media Calendar* removes the calendar mode from that
action, so the Posts menu keeps working with its kanban, list and form views.
