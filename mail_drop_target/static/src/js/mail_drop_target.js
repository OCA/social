/* global Uint8Array base64js*/
odoo.define("mail_drop_target", function (require) {
    "use strict";

    const MessageList = require("mail/static/src/components/message_list/message_list.js");
    const {patch} = require("web.utils");
    const DropZone = require("mail/static/src/components/drop_zone/drop_zone.js");
    const useDragVisibleDropZone = require("mail/static/src/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone.js");

    patch(MessageList, "mail_drop_target.mail_drop", {
        setup() {
            this._super();
            this.isDropZoneVisible = useDragVisibleDropZone();
        },
        async _onDropZoneFilesDropped(ev) {
            ev.stopPropagation();
            this.isDropZoneVisible.value = false;
            var self = this;
            Promise.all(
                Array.from(ev.detail.files).map((drop_file) => {
                    var reader = new FileReader();
                    var mail_processor = "";
                    if (drop_file.name.endsWith(".msg")) {
                        mail_processor = "message_process_msg";
                    } else {
                        mail_processor = "message_drop";
                    }
                    reader.readAsArrayBuffer(drop_file);
                    reader.onload = function (event) {
                        var data = "";
                        // TODO: read some config parameter if this should set
                        // some of the context keys to suppress mail.thread's behavior
                        if (mail_processor === "message_process_msg") {
                            data = base64js.fromByteArray(
                                new Uint8Array(event.target.result)
                            );
                        } else {
                            var reader_array = new Uint8Array(event.target.result);
                            data = "";
                            for (var i = 0; i < reader_array.length; i++) {
                                data += String.fromCharCode(
                                    parseInt(reader_array[i], 10)
                                );
                            }
                        }
                        self.env.services.rpc({
                            model: "mail.thread",
                            method: mail_processor,
                            args: [self.threadView.thread.model, data],
                            kwargs: {
                                thread_id: self.threadView.thread.id,
                            },
                        });
                    };
                })
            ).then(function () {
                return self.trigger("reload");
            });
        },
    });
    MessageList.components.DropZone = DropZone;
});
