/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

/**
 * The dark palette of the social media screens.
 *
 * The choice is stored on the user, not in the browser, so it follows the
 * person to any device. The class lives on the body because the form and the
 * dashboard are different actions and the palette has to survive a reload.
 */
export class SocialDarkModeSystray extends Component {
    static template = "social_media_base.SocialDarkModeSystray";

    setup() {
        this.orm = useService("orm");
        this.state = useState({dark: false, loaded: false});
        onWillStart(async () => {
            this.state.dark = await this.orm.call(
                "res.users",
                "get_social_dark_mode",
                []
            );
            this.apply();
            this.state.loaded = true;
        });
    }

    apply() {
        document.body.classList.toggle("o_social_dark", this.state.dark);
    }

    async toggle() {
        const previous = this.state.dark;
        this.state.dark = !previous;
        this.apply();
        try {
            await this.orm.call("res.users", "set_social_dark_mode", [this.state.dark]);
        } catch {
            // Never leave the screen in a palette the user did not ask for.
            this.state.dark = previous;
            this.apply();
        }
    }
}

registry.category("systray").add("social_media_base.SocialDarkMode", {
    Component: SocialDarkModeSystray,
    sequence: 60,
});
