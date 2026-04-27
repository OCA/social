**Global Configuration (Company-wide):**

#. Go to Settings → General Settings
#. In the "Allowed Attachment Types" field, enter comma-separated MIME types
#. Example: ``image/png,application/pdf``
#. Leave empty to allow all file types

**Per-Model Configuration (Optional):**

#. Go to Settings → Technical → Database Structure → Models
#. Select a model (e.g., "Contact" for res.partner)
#. In the "Allowed Attachment Types" field, enter comma-separated MIME types
#. Empty value = use global config; set value = override global config

**Configuration Hierarchy:**

Per-model settings override global settings when defined.
