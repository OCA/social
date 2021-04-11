To configure this module, you need to:

#. Go to *Settings > General Settings > Messages > Activities Redirection*.

#. Open configuration tool using *Redirect activities to a specific user*.

#. Create or edit a redirection.

#. Configure rules properly, note that the only mandatory field is `user`, it's
   this user that will be assigned to this activity, all other fields are the
   redirection rules:

  * `Users initially targeted` is the list of internal users initially
    targeted by this activity.

  * `Models`, like the above list, is a set of models targeted by this
    activity.

  * `Activity types`, is another way to filter more finely the current
    activity, for example we can filter only on `exception` type activities.

  * `QWeb Templates`, is a good way to be sure to redirect an activity
    pre-designed as a template. It should be preferred over a `RegEx` rule.

  * `RegEx`, when no QWeb template exists, is the last way to intercept an
    activity. It must be the last way to make a match since it depends of the
    current translation. For an effective multine parsing, MULTILINE and
    DOTALL flags are enabled.

.. note::
  Rules are analyzed in the same order in which they appear in the model view.
  An empty redirect rule is ignored. The redirect analysis stops as soon as a
  rule does not match.
