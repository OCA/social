# Copyright 2018 David Juaneda - <djuaneda@sdi.es>
# Copyright 2021 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class MailActivityMixin(models.AbstractModel):
    _inherit = "mail.activity.mixin"

    def redirect_to_activities(self, **kwargs):
        """Redirects to the list of activities of the object shown.

        Redirects to the activity board and configures the domain so that
        only those activities that are related to the object shown are
        displayed.

        Add to the title of the view the name the class of the object from
        which the activities will be displayed.

        :param kwargs: contains the id of the object and the model it's about.

        :return: action.
        """
        _id = kwargs.get("id")
        model = kwargs.get("model")
        action = self.env["mail.activity"].action_activities_board()
        views = []
        for v in action["views"]:
            if v[1] == "tree":
                v = (v[0], "list")
            views.append(v)
        action["views"] = views
        action["domain"] = [("res_id", "=", _id), (("res_model", "=", model))]
        return action
