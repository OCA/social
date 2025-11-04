import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useRef,
    useState,
} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";
import {Popover} from "@web/core/popover/popover";
import {browser} from "@web/core/browser/browser";

export class SocialAccount extends Component {
    static template = "social_media_base.SocialAccount";
    static props = {
        socialAccounts: {type: Array},
    };

    setup() {
        super.setup();
        this.orm = useService("dialog");
        this.dashboard = useRef("dashboard");
        this.popovers = [];
        this.state = useState({
            needUpdate: false,
        });

        onWillStart(async () => {
            this.state.needUpdate =
                this.props.socialAccounts.filter((item) => item.need_update).length > 0;
        });

        onMounted(() => this._initPopovers());

        onWillUnmount(() => this._disposePopovers());

        useBus(this.env.bus, "SOCIAL:NEED-UPDATE", async ({detail: data}) => {
            this.state.needUpdate = data.needUpdate;
        });
    }

    _initPopovers() {
        // Initialize Bootstrap popovers for metric tooltips
        // Popover is available globally from Bootstrap
        if (typeof Popover !== "undefined") {
            const popoverElements = browser.document.querySelectorAll(
                '[data-bs-toggle="popover"]'
            );
            popoverElements.forEach((el) => {
                this.popovers.push(
                    new Popover(el, {
                        trigger: "hover",
                        delay: {show: 500, hide: 0},
                    })
                );
            });
        }
    }

    _disposePopovers() {
        this.popovers.forEach((popover) => {
            popover.dispose();
        });
        this.popovers = [];
    }
}
