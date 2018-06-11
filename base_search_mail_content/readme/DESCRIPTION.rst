This module adds the capability to find on any object (e.g. project issues or
helpdesk ticket) based on the conversation threads associated to them.

This will be useful in models that make intense use of messages,
like project issues or helpdesk tickets.

A project issue or helpdesk ticket can contain tens of mails or notes
associated, based on the feedback that the person responsible for the ticket
maintains, including conversations with the person that raised the issue.

A user may often want to find issues or tickets, based on the past
conversations that were recorded, as much as he or she needs to search
in their mail for past conversations.

This module will add dynamically a field 'message_content' to the search view
of any model that inherits from the mail.thread.

The current search capabilities include searching into the subject, body,
email from, reply to and record name.
