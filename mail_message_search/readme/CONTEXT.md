This module offers an alternative to `base_search_mail_content`, designed to better
support languages that do not separate words with spaces (e.g., Chinese, Japanese,
Korean, Thai).

The original module relies on PostgreSQL's `pg_trgm`, which requires three-character
tokens and a similarity score above the default cutoff—making it ineffective for
languages without space-separated words.

This module uses direct keyword matching across key fields in `mail.message`, offering
more reliable results in multilingual environments.
