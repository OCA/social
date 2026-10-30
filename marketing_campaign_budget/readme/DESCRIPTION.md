This module extends the standard `utm.campaign` model with basic financial
planning fields:

- Budget Amount
- Actual Cost

Both fields use the company currency.

This module only stores campaign planning information. Profitability and
ROI calculations are intentionally left out, and can be implemented later
by separate modules. It does not modify the existing `stage_id` workflow.
