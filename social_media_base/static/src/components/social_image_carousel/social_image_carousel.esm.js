import {Component, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";

export class SocialImageCarousel extends Component {
    static template = "social_media_base.SocialImageCarousel";
    static components = {Dialog};
    static props = {
        images: Array,
        startIndex: {type: Number, optional: true},
        close: Function,
    };

    setup() {
        this.state = useState({
            currentIndex: this.props.startIndex || 0,
        });
    }

    get currentImage() {
        return this.props.images[this.state.currentIndex];
    }

    get hasPrevious() {
        return this.state.currentIndex > 0;
    }

    get hasNext() {
        return this.state.currentIndex < this.props.images.length - 1;
    }

    previousImage() {
        if (this.hasPrevious) {
            this.state.currentIndex--;
        }
    }

    nextImage() {
        if (this.hasNext) {
            this.state.currentIndex++;
        }
    }

    onKeydown(ev) {
        if (ev.key === "ArrowLeft") {
            this.previousImage();
        } else if (ev.key === "ArrowRight") {
            this.nextImage();
        } else if (ev.key === "Escape") {
            this.props.close();
        }
    }
}
