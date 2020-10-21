/** ********************************************************************************
    Copyright 2020 Creu Blanca
    License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
 **********************************************************************************/

odoo.define("audio_file.preview", function (require) {
    "use strict";

    var preview = require("mail_preview_base.preview");
    var DocumentViewer = preview.DocumentViewer;

    DocumentViewer.include({
        _checkAttachment: function (attachment) {
            if (
                attachment.type !== 'url' && attachment.mimetype.match("audio")
            ) {
                attachment.type = 'audio';
                attachment.source_url = this._getImageUrl(attachment);
                return true;
            }
            return this._super.apply(this, arguments);
        },
        _hasPreview: function (type) {
            var result = this._super.apply(this, arguments);
            return result || type === 'audio';
        },
    });

});
