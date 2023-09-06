odoo.define("mail_activity_team/static/src/components/activity/activity.js", function (
    require
) {
    "use strict";

    const components = {
        Activity: require("mail/static/src/components/activity/activity.js"),
    };
    const {patch} = require("web.utils");

    patch(
        components.Activity,
        "mail_activity_team/static/src/components/activity/activity.js",
        {
            /**
             * Note that Odoo 14.0 does not allow patching a getter with. For more
             * informations, read Solution 4 from:
             * https://codingdodo.com/owl-in-odoo-14-extend-and-patch-existing-owl-components/
             * @returns {String}
             */
            assignedTeamText() {
                return _.str.sprintf(
                    this.env._t("for %s"),
                    this.activity.team.displayName
                );
            },
        }
    );
});
