import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useRef,
    useState,
} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";

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
        const bootstrap = globalThis.window.bootstrap;
        if (bootstrap && bootstrap.Popover) {
            const popoverElements = globalThis.document.querySelectorAll(
                '[data-bs-toggle="popover"]'
            );
            popoverElements.forEach((el) => {
                this.popovers.push(
                    new bootstrap.Popover(el, {
                        trigger: "hover",
                        delay: {show: 500, hide: 0},
                    })
                );
            });
        }
    }

    _disposePopovers() {
        if (this.popovers) {
            this.popovers.forEach((popover) => {
                if (popover && typeof popover.dispose === "function") {
                    popover.dispose();
                }
            });
            this.popovers = [];
        }
    }
}
