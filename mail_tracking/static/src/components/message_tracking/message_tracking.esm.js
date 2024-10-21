const {Component, useState} = owl;

export class MessageTracking extends Component {
    static template = "mail_tracking.MessageTracking";
    static props = ["message", "partner_trackings", "skip_track_links?"];
    setup() {
        this.message = useState(this.props.message);
        this.partner_trackings = useState(this.props.partner_trackings);
    }
    _onTrackingStatusClick(event) {
        const tracking_email_id = event.currentTarget.dataset.tracking;
        event.preventDefault();
        return this.env.services.action.doAction({
            type: "ir.actions.act_window",
            view_type: "form",
            view_mode: "form",
            res_model: "mail.tracking.email",
            views: [[false, "form"]],
            target: "new",
            res_id: parseInt(tracking_email_id),
        });
    }
}
