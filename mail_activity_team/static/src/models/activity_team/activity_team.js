odoo.define(
    "mail_activity_team/static/src/models/activity_team/activity_team.js",
    function (require) {
        "use strict";

        const {registerNewModel} = require("mail/static/src/model/model_core.js");
        const {attr} = require("mail/static/src/model/model_field.js");

        function factory(dependencies) {
            class ActivityTeam extends dependencies["mail.model"] {}

            ActivityTeam.fields = {
                displayName: attr(),
                id: attr(),
            };

            ActivityTeam.modelName = "mail.activity_team";

            return ActivityTeam;
        }

        registerNewModel("mail.activity_team", factory);
    }
);
