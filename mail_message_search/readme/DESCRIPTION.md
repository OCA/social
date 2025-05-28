This module enables searching for messages across any record that uses the chatter,
based on their associated conversation threads. It dynamically adds a Message Search
field to the search view of any model that inherits from `mail.thread`.

The Message Search field performs a smart, per-word search across a message’s subject,
body, sender, and reply-to fields.
