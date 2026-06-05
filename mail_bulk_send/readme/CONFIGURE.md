Create an `ir.actions.server` record for each model you want to support.
Set **Action To Do** to *Execute Python Code* and enter the following,
replacing the template reference with the one you want to use:

```python
action = {
    "type": "ir.actions.act_window",
    "res_model": "mail.bulk.send.wizard",
    "view_mode": "form",
    "target": "new",
    "context": {
        **env.context,
        "default_template_id": env.ref("module_name.template_xml_id").id,
    },
}
```

- `**env.context` passes the selected record IDs and model to the wizard
  automatically.
- `default_template_id` pre-selects the template and locks the field so
  users cannot change it. Omit this key to let users choose the template
  themselves.

Set **Binding Model** to the target model and **Binding View Types** to
`list` so the action appears in the **Action** menu of the list view.
