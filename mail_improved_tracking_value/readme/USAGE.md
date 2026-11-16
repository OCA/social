Read the ids of the tracked changes of any tracked many2many or one2many
field, for example the tags of the applicants (`hr_recruitment`):

```python
field = env["ir.model.fields"]._get("hr.applicant", "categ_ids")
env["mail.tracking.value"].search_read(
    [("field_id", "=", field.id)],
    ["old_value_char", "new_value_char", "old_value_text", "new_value_text"],
)
# [{'old_value_char': 'Tag A', 'new_value_char': 'Tag A, Tag B',
#   'old_value_text': '[1]', 'new_value_text': '[1, 2]', ...}]
```

`json.loads()` turns `old_value_text` and `new_value_text` into lists of ids.
