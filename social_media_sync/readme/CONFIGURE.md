Nothing has to be configured for this module to work: it uses the accounts,
the credentials and the groups of *Social Media Base*.

What is worth reviewing is the two scheduled actions it adds, in
*Settings / Technical / Automation / Scheduled Actions*:

- *Social: Initial sync of the new accounts* runs monthly, and is also
  triggered on the spot every time an account is linked. It only picks up the
  accounts still waiting for that first import, so the monthly run is a safety
  net rather than the normal path.
- *Social: Full resync of the accounts* runs weekly. It is the only pass that
  notices a publication deleted on the social media, and the most expensive
  one: it reads every publication of every account, one call per page. Making
  it run more often is what turns a deletion noticed a few days late into a
  quota problem.

Both intervals are the ones to move if the social media of an account is
strict about quotas.
