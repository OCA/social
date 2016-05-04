/* © 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

"use strict";
(function ($) {
    $("#reason_form :radio").change(function(event) {
        $("textarea[name=details]").attr(
            "required",
            $(event.target).is("[data-details-required]")
        );
    });
    $("#reason_form :radio:checked").change();
})(jQuery);
