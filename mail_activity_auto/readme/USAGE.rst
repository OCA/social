To set activities as automatic:

#. Go to Settings -> Technical -> Activity Types
#. Create or edit Activity Type to set automatic.
#. Add actions with domain.

#. Create activity with automatic activity type.
#. Queue Job will be created to execute related actions on date and time deadline.
#. For each action set on activity type, if domain is True then Queue Job will execute server action.
#. If you cancel, update or execute activity before date and time deadline, queue job will be cancel, update or execute.
#. Also you can create an Activity Type with Server Action without set it automatic, then Server Action will be executed when you set activity as done.
