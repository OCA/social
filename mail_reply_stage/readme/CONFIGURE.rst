Go to **Settings > Technical > Email > Mail Reply Configurations** and create records
according to your needs.

For each record:

- **Model**: Choose a model (required).
- **Parent Field**: Select the many2one field that links to the parent model.
  For example, if you select the model `project.task`, choose `project_id` as the parent
  field.
- **Parent Stage Field**: Choose the many2many field from the model of Parent Field that defines
  the allowed stages.The system will check whether the selected Reply Stage is
  included in the value of this field.
  If the Reply Stage is not present in the Parent Stage Field, it will not be assigned to
  the record.
- **domain**: Set a domain to filter which records this config applies to.
  Example: ``[('project_id.name', '=', 'My Project')]``
- **Reply Stage Field**: Choose the field (e.g., `stage_id`) to be updated when a
  non-internal user replies. (required)
- **Reply Stage**: Set the name of the stage to apply on reply. (required)

Examples
~~~~~~~~

Example 1 – For "Office Design" Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This rule applies to tasks under the **"Office Design"** project.

+------------------------+-------------------------------------------------------------+
| **Field**              | **Value**                                                   |
+========================+=============================================================+
| Model                  | Task (``project.task``)                                     |
+------------------------+-------------------------------------------------------------+
| Parent Field           | Project (``project_id``)                                    |
+------------------------+-------------------------------------------------------------+
| Parent Stage Field     | Task Stages (``project.task.type_ids``)                     |
+------------------------+-------------------------------------------------------------+
| Domain                 | ``[('project_id.name', '=', 'Office Design')]``             |
+------------------------+-------------------------------------------------------------+
| Reply Stage Field      | Stage (``stage_id``)                                        |
+------------------------+-------------------------------------------------------------+
| Reply Stage            | Reply to Customer                                           |
+------------------------+-------------------------------------------------------------+

Example 2 – Fallback for All Other Projects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This rule applies to all tasks that do **not** belong to the "Office Design" project.

+------------------------+-------------------------------------------------------------+
| **Field**              | **Value**                                                   |
+========================+=============================================================+
| Model                  | Task (``project.task``)                                     |
+------------------------+-------------------------------------------------------------+
| Parent Field           | Project (``project_id``)                                    |
+------------------------+-------------------------------------------------------------+
| Parent Stage Field     | Task Stages (``project.task.type_ids``)                     |
+------------------------+-------------------------------------------------------------+
| Domain                 |                                                             |
+------------------------+-------------------------------------------------------------+
| Reply Stage Field      | Stage (``stage_id``)                                        |
+------------------------+-------------------------------------------------------------+
| Reply Stage            | Need Discussion                                             |
+------------------------+-------------------------------------------------------------+

Use the up/down arrows to prioritize the rules.
The system evaluates rules from top to bottom and applies only the first matching one.
Place more specific rules (with a domain) above general ones (e.g., fallback rules with an empty domain).

Based on the two example configurations:
For a task under the "Office Design" project, both rules match.
However, the first rule at the top will be used.

Note: Make sure the selected reply stage exists in the parent record’s allowed stages,
as defined by the **Parent Stage Field**.
