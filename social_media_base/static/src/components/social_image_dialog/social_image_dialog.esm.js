/** @odoo-module **/

import {Component, useRef, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";

export class SocialImageDialog extends Component {
    static template = "social_media_base.SocialImageDialog";
    static props = {
        images: {type: Array, required: true},
        title: {type: String, optional: true},
        fullscreen: {type: Boolean, optional: true},
        close: {type: Function, optional: true},
    };
    static components = {
        Dialog,
    };

    /**
     * Setups the component.
     *
     * @private
     * @override
     */
    setup() {
        super.setup();
        this.carouselRef = useRef("carouselRef");
        this.state = useState({
            imageUrlActive: this.props.images[0],
        });
    }

    /**
     * Returns the currently active image URL based on navigation direction.
     *
     * @param {Boolean} [prev=false] - If true, navigate to the previous image.
     * @param {Boolean} [next=false] - If true, navigate to the next image.
     * @returns {String} The URL of the new active image.
     */
    indexImageActive(prev = false, next = false) {
        let current_index = this.props.images.indexOf(this.state.imageUrlActive);
        if (prev) {
            current_index =
                (current_index === 0 ? this.props.images.length : current_index) - 1;
        } else if (next) {
            current_index = (current_index + 1) % this.props.images.length;
        }
        return this.props.images[current_index];
    }

    /**
     * Updates the active image to the previous one in the list.
     *
     * - Calls `indexImageActive` with `prev` set to true to get the URL of the previous image.
     * - Updates the `imageUrlActive` state with the new active image URL.
     */
    prevImage() {
        this.state.imageUrlActive = this.indexImageActive(true);
    }

    /**
     * Updates the active image to the next one in the list.
     *
     * - Calls `indexImageActive` with `next` set to true to get the URL of the next image.
     * - Updates the `imageUrlActive` state with the new active image URL.
     */
    nextImage() {
        this.state.imageUrlActive = this.indexImageActive(false, true);
    }
}
