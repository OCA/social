To configure this module, you need to go to System parameters and adjust
mail_restrict_follower_selection.domain as you see fit. This restricts
followers globally, if you want to restrict only the followers for a
certain record type (or have different restrictions for different record
types), create a parameter
mail_restrict_follower_selection.domain.\$your_model.

As an example, you could use \[('category_id.name', '=', 'Employees')\]
to allow only contacts with 'Employees' tag to be added as follower -
this also is the default.

Note: This module won't change existing followers!
