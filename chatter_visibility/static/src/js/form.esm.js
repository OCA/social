import {FormController} from "@web/views/form/form_controller";
import {cookie as cookieManager} from "@web/core/browser/cookie";
import {onMounted} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
const {document, Element} = globalThis;

// Extend DOM Element prototype to add jQuery-like hide/show methods.
// This provides a clean API similar to jQuery without the dependency.
if (!Element.prototype.hide) {
    Element.prototype.hide = function () {
        this.style.display = "none";
        return this;
    };
}

if (!Element.prototype.show) {
    Element.prototype.show = function () {
        this.style.display = "block";
        return this;
    };
}

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
        onMounted(async () => {
            this.injectToggleButtons();
            const res = await this.orm.call("res.users", "get_chatter_visibility", []);
            if (res && !res.show_chatter) {
                this.setChatterVisibility(false);
            } else {
                this.setChatterVisibility(true);
            }
        });
    },

    injectToggleButtons() {
        if (document.querySelector(".custom-ovn-wrapper")) {
            return;
        }
        const formSheet = document.querySelector(".o_form_sheet_bg");
        if (!formSheet) {
            return;
        }
        const wrapper = document.createElement("div");
        wrapper.className = "custom-ovn-wrapper";
        wrapper.style.marginTop = "auto";
        wrapper.style.marginBottom = "auto";
        const ShowBtn = document.createElement("button");
        ShowBtn.className = "btn btn-show";
        ShowBtn.title = "Show Chatter";
        ShowBtn.onclick = () => this.setChatterVisibility(true);

        const HideBtn = document.createElement("button");
        HideBtn.className = "btn btn-hide";
        HideBtn.title = "Hide Chatter";
        HideBtn.onclick = () => this.setChatterVisibility(false);

        // Default (light mode) - If not dark mode then use black icons.
        ShowBtn.innerHTML =
            "<img src='/chatter_visibility/static/img/chatter_show_black.png' alt='chatter show' width='30' height='30'>";
        HideBtn.innerHTML =
            "<img src='/chatter_visibility/static/img/chatter_hide_black.png' alt='chatter hide' width='30' height='30'>";

        // Dark mode - If dark mode is enabled, use white icons.
        if (cookieManager.get("color_scheme") === "dark") {
            ShowBtn.innerHTML =
                "<img src='/chatter_visibility/static/img/chatter_show_white.png' alt='chatter show' width='30' height='30'>";

            HideBtn.innerHTML =
                "<img src='/chatter_visibility/static/img/chatter_hide_white.png' alt='chatter hide' width='30' height='30'>";
        }
        const ChatterContainer = document.querySelector(".o-mail-ChatterContainer");
        if (ChatterContainer) {
            wrapper.appendChild(ShowBtn);
            wrapper.appendChild(HideBtn);
            formSheet.parentNode.insertBefore(wrapper, formSheet.nextSibling);
        }
    },

    setChatterVisibility(show) {
        const ChatterContainer = document.querySelector(".o-mail-ChatterContainer");
        const formSheetBg = document.querySelector(".o_form_sheet_bg");
        const HideBtn = document.querySelector(".btn-hide");
        const ShowBtn = document.querySelector(".btn-show");

        if (show) {
            ChatterContainer?.show();
            HideBtn?.show();
            ShowBtn?.hide();
        } else {
            ChatterContainer?.hide();
            HideBtn?.hide();
            ShowBtn?.show();
        }

        if (formSheetBg) {
            formSheetBg.style.maxWidth = show ? "1534px" : "none";
        }
    },
});
