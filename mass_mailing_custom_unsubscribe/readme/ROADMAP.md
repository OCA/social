- We use an alternative model to the core `mailing.subscription` as that one is
  constrained to mailing/lists and we aim to register other models opt outs as well.
  Maybe we could merge `mail.unsubscription` with it but it requires such a
  transformation that is like replacing it completely with our own logic, so we'd be
  just avoiding to have these two sources of information while we'd be probably dealing
  with the potential side-effects of changing core's logic...
