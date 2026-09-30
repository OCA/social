/** @odoo-module **/

import {Composer} from "@mail/core/common/composer";

/**
 * The composer of the dialog, saying while it is publishing.
 *
 * `Composer` guards against sending the same message twice with
 * `state.active`, which lives in the component. This one is drawn under the
 * comment being answered, so it is destroyed and built again whenever the aim
 * moves, and the instance that takes over is born with that guard open while
 * the text is still on the record the two of them share. Saying when a
 * publication is in flight is what lets the dialog hold the aim still until
 * it lands.
 */
export class SocialComposer extends Composer {
    static props = [...Composer.props, "onPostingChange?"];

    async processMessage(cb) {
        this.props.onPostingChange?.(true);
        try {
            await super.processMessage(cb);
        } finally {
            this.props.onPostingChange?.(false);
        }
    }
}
