//-*- coding: utf-8 -*-
//Copyright 2018 Therp BV <https://therp.nl>
//License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

odoo.define('mail_drop_target', function(require)
{
    var Chatter = require('mail.Chatter'),
        web_drop_target = require('web_drop_target'),
        Model = require('web.Model');

    Chatter.include(web_drop_target.DropTargetMixin);
    Chatter.include({
        _drop_allowed_types: ['message/rfc822'],
        _get_drop_item: function(e) {
            var dataTransfer = e.originalEvent.dataTransfer;
            if(
                dataTransfer.items.length == 1 &&
                dataTransfer.items[0].type == '' &&
                dataTransfer.items[0].kind == 'file'
            ) {
                // this might be an outlook msg file
                return dataTransfer.items[0];
            }
            return this._super.apply(this, arguments);
        },
        _handle_file_drop: function(drop_file, e) {
            var self = this,
                mail_processor = '',
                data = '';
            if(drop_file.name.endsWith('.msg')) {
                mail_processor = 'message_process_msg';
                data = base64js.fromByteArray(
                    new Uint8Array(e.target.result)
                );
            } else {
                mail_processor = 'message_process';
                data = String.fromCharCode.apply(
                    null, new Uint8Array(e.currentTarget.result)
                );
            }
            // TODO: read some config parameter if this should set
            // some of the context keys to suppress mail.thread's behavior
            return new Model('mail.thread').call(
                mail_processor,
                [this.field_manager.dataset.model, data],
                {
                    thread_id: this.field_manager.datarecord.id,
                }
            )
            .then(function() {
                return self.field_manager.reload();
            });
        }
    });
});
