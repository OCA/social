/* © 2016 Antiun Ingeniería S.L. - Jairo Llopis
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */

"use strict";
(function ($) {
    var _t = openerp._t,
        prompt = openerp.website.prompt,
        snippet = openerp.website.snippet;

    snippet.options.vertical_resize = snippet.Option.extend({
        start: function () {
            var self = this;
            self._super();
            return self.$el.find(".js_vertical_resize").click(function(){
                return self.ask();
            });
        },

        ask: function() {
            var self = this;
            return prompt({
                window_title: _t("Set element height"),
                input: _t("Element height in pixels"),
            }).then(function (answer) {
                return self.resize(answer);
            });
        },

        resize: function(size) {
            this.$target.css("height", String(size) + "px");

            // Old-school height attribute changed too if needed
            if (this.$target.attr("height")) {
                this.$target.attr("height", size);
            }
        },
    });
})(jQuery);
