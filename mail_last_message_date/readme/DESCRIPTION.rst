This module does not provide functionality on its own; another module must inherit 
``mail.last.message.date.mixin`` on the target model. This module adds a last chatter 
update datetime (``last_message_date``) through the mixin. Models inherit the mixin
explicitly, and can optionally restrict updates to specific message_type in code.
