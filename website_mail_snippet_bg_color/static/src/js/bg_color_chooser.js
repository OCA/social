/* © 2016 Antiun Ingeniería S.L. - Jairo Llopis
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */

"use strict";
(function ($) {
    var snippet = openerp.website.snippet;

    snippet.options.bg_color_chooser = snippet.Option.extend({
        start: function () {
            var self = this;
            self._super();
            return self.$el.find(".js_bg_color_chooser").click(function(){
                return self.choose();
            });
        },

        choose: function() {
            var self = this;
            return CKEDITOR.instances.wrapwrap.getColorFromDialog(
                function(color){
                    return self.change(color);
                }
            );
        },

        change: function(color) {
            this.$target.css("background-color", color);

            // Old-school bgcolor attribute if the element already had one
            if (this.$target.attr("bgcolor")) {
                this.$target.attr("bgcolor", color);
            }
        },
    });
})(jQuery);
