This module adds some attributes that can be used in the
``default_description`` field of ``mail.activity.type``:

data-form-id
    A name used to refer to the content of this node afterwards
data-form-type
    One of 'float', 'int', 'str'
data-form-editable
    Only nodes marked with this attribute may be edited in activities
data-form-compute
    An expression to evaluate, ``object`` can be used to access values of the
    object the activity is attached to, and ``activity`` for the activity
    itself

Note that the above implies that you shouldn't use ``object`` and ``activity``
in the ``data-form-id`` attribute.
