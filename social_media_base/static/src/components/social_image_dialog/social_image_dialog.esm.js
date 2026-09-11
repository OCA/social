/** @odoo-module **/

import {Component, useState} from "@odoo/owl";
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

    /** @override */
    setup() {
        super.setup();
        this.state = useState({
            imageUrlActive: this.props.images[0],
        });
    }

    indexImageActive(prev = false, next = false) {
        let currentIndex = this.props.images.indexOf(this.state.imageUrlActive);
        if (prev) {
            currentIndex =
                (currentIndex === 0 ? this.props.images.length : currentIndex) - 1;
        } else if (next) {
            currentIndex = (currentIndex + 1) % this.props.images.length;
        }
        return this.props.images[currentIndex];
    }

    prevImage() {
        this.state.imageUrlActive = this.indexImageActive(true);
    }

    nextImage() {
        this.state.imageUrlActive = this.indexImageActive(false, true);
    }
}
