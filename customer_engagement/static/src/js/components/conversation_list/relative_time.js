/** @odoo-module **/

import {Component, onMounted, onWillUnmount, useState} from "@odoo/owl";

export class RelativeTime extends Component {
    static template = "customer_engagement.RelativeTime";
    static props = {
        datetime: {type: [String, Boolean], optional: true},
        format: {type: String, optional: true}, // "short", "long"
    };

    setup() {
        this.state = useState({
            displayText: this.computeRelativeTime(),
        });

        this.intervalId = null;

        onMounted(() => {
            // Update every minute
            this.intervalId = setInterval(() => {
                this.state.displayText = this.computeRelativeTime();
            }, 60000);
        });

        onWillUnmount(() => {
            if (this.intervalId) {
                clearInterval(this.intervalId);
            }
        });
    }

    computeRelativeTime() {
        if (!this.props.datetime) {
            return "";
        }

        const date = new Date(this.props.datetime);
        const now = new Date();
        const diff = now - date;

        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        const weeks = Math.floor(days / 7);

        const isShort = this.props.format === "short";

        if (seconds < 60) {
            return isShort ? "now" : "just now";
        }
        if (minutes < 60) {
            return isShort
                ? `${minutes}m`
                : `${minutes} minute${minutes !== 1 ? "s" : ""} ago`;
        }
        if (hours < 24) {
            return isShort ? `${hours}h` : `${hours} hour${hours !== 1 ? "s" : ""} ago`;
        }
        if (days < 7) {
            return isShort ? `${days}d` : `${days} day${days !== 1 ? "s" : ""} ago`;
        }
        if (weeks < 4) {
            return isShort ? `${weeks}w` : `${weeks} week${weeks !== 1 ? "s" : ""} ago`;
        }

        // For older dates, show the actual date
        return date.toLocaleDateString();
    }

    get fullDateTime() {
        if (!this.props.datetime) {
            return "";
        }
        const date = new Date(this.props.datetime);
        return date.toLocaleString();
    }
}
