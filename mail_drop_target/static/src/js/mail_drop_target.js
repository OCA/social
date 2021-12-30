/* global base64js:false, Uint8Array:false */
// Copyright 2018 Therp BV <https://therp.nl>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

odoo.define("mail_drop_target", function (require) {
    "use strict";
    var Chatter = require("mail.Chatter");
    var web_drop_target = require("web_drop_target");

    Chatter.include(web_drop_target.DropTargetMixin);

    Chatter.include({
        _drop_allowed_types: ["message/rfc822"],
        _get_record_id: function () {
            return this.record.res_id;
        },

        _handle_drop_items: function (drop_items) {
            var self = this;
            _.each(drop_items, function (item, e) {
                return self._handle_file_drop_proxy(item, e);
            });
        },
        _handle_file_drop_proxy: function (item, e) {
            var self = this;
            var file = item;
            if (!file || !(file instanceof Blob)) {
                return;
            }
            var reader = new FileReader();
            reader.onloadend = self.proxy(
                _.partial(self._handle_file_drop, file, reader, e)
            );
            reader.onerror = self.proxy("_file_reader_error_handler");
            reader.readAsArrayBuffer(file);
        },
        _handle_file_drop: function (drop_file, reader) {
            var self = this,
                mail_processor = "",
                data = "";
            if (drop_file.name.endsWith(".msg")) {
                mail_processor = "message_process_msg";
                data = base64js.fromByteArray(new Uint8Array(reader.result));
            } else {
                mail_processor = "message_drop";
                var reader_array = new Uint8Array(reader.result);
                data = "";
                for (var i = 0; i < reader_array.length; i++) {
                    data += String.fromCharCode(parseInt(reader_array[i]));
                }
            }
            // TODO: read some config parameter if this should set
            // some of the context keys to suppress mail.thread's behavior
            return this._rpc({
                model: "mail.thread",
                method: mail_processor,
                args: [this.record.model, data],
                kwargs: {
                    thread_id: this.record.data.id,
                },
            }).then(function () {
                self.trigger_up("reload", {});
            });
        },
    });
});
