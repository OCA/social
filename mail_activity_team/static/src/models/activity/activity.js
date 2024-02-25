odoo.define("mail_activity_team/static/src/models/activity/activity.js", function (
    require
) {
    "use strict";

    const {
        registerClassPatchModel,
        registerInstancePatchModel,
        registerFieldPatchModel,
    } = require("mail/static/src/model/model_core.js");
    const {many2one} = require("mail/static/src/model/model_field.js");

    registerClassPatchModel(
        "mail.activity",
        "mail_activity_team/static/src/models/activity/activity.js",
        {
            convertData(data) {
                const data2 = this._super(data);
                if ("team_id" in data) {
                    if (!data.team_id) {
                        data2.team = [["unlink-all"]];
                    } else {
                        data2.team = [
                            [
                                "insert",
                                {
                                    id: data.team_id[0],
                                    displayName: data.team_id[1],
                                },
                            ],
                        ];
                    }
                }
                return data2;
            },
        }
    );

    registerInstancePatchModel(
        "mail.activity",
        "mail_activity_team/static/src/models/activity/activity.js",
        {}
    );

    registerFieldPatchModel(
        "mail.activity",
        "mail_activity_team/static/src/models/activity/activity.js",
        {
            /**
             * Team linked to this activity.
             */
            team: many2one("mail.activity_team"),
        }
    );
});
