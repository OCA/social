/** @odoo-module **/
/* Copyright 2020 Creu Blanca
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).*/

import {DocumentViewer} from "mail_preview_base.preview";

DocumentViewer.include({
    _checkAttachment: function (attachment) {
        if (attachment.type !== "url" && attachment.mimetype.match("audio")) {
            attachment.type = "audio";
            attachment.source_url = this._getImageUrl(attachment);
            return true;
        }
        return this._super(...arguments);
    },
    _hasPreview: function (type) {
        return this._super(...arguments) || type === "audio";
    },
});
