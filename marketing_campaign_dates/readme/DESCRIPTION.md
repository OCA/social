This module extends the standard `utm.campaign` model with time management
fields:

- Start Date
- End Date

It also adds three date-based filters to the campaign search view:

- **Running** -- campaigns that have started and are not yet finished
- **Upcoming** -- campaigns that have not started yet
- **Finished** -- campaigns that have already ended

This module is a lightweight foundation for future reporting and analytics
(e.g. ROI, profitability), to be handled by separate modules. It does not
modify the existing marketing workflow and reuses the standard `stage_id`.
