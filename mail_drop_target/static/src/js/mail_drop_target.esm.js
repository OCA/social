/** @odoo-module **/
/* global base64js:false, Uint8Array:false */
// Copyright 2018 Therp BV <https://therp.nl>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import {Chatter} from "@mail/components/chatter/chatter";
import {patch} from "web.utils";
import {useDragVisibleDropZone} from "@mail/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone";
const {useRef} = owl.hooks;

patch(Chatter.prototype, "mail_drop_target.mail_drop", {
    setup() {
        this._super();
        this.isDropZoneVisible = useDragVisibleDropZone();
        this._fileUploaderRef = useRef("fileUploader");
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
                } else if (drop_file.name.endsWith(".eml")) {
                    mail_processor = "message_drop";
                } else {
                    this._fileUploaderRef.comp.uploadFiles(ev.detail.files);
                    this.chatter.update({isAttachmentBoxVisible: true});
                }
                if (mail_processor) {
                    reader.readAsArrayBuffer(drop_file);
                    reader.onload = function (event) {
                        var data = "";
                        // TODO: read some config parameter if this should set
                        // some of the context keys to suppress mail.thread's behavior
                        if (mail_processor == "message_process_msg") {
                            data = base64js.fromByteArray(
                                new Uint8Array(event.target.result)
                            );
                        } else {
                            var reader_array = new Uint8Array(event.target.result);
                            data = "";
                            for (var i = 0; i < reader_array.length; i++) {
                                data += String.fromCharCode(parseInt(reader_array[i]));
                            }
                        }
                        self.env.services.rpc({
                            model: "mail.thread",
                            method: mail_processor,
                            args: [self.chatter.thread.model, data],
                            kwargs: {
                                thread_id: self.chatter.thread.id,
                            },
                        });
                    };
                }
            })
        ).then(function () {
            return self.trigger("reload");
        });
    },
});
