odoo.define('mail_tracking/static/src/js/chatter.js', function (require) {
'use strict';

const ChatterContainer = require('mail/static/src/components/chatter_container/chatter_container.js');
const { attr } = require('mail/static/src/model/model_field.js');
const { registerInstancePatchModel,registerFieldPatchModel,    registerClassPatchModel,
 } = require('mail/static/src/model/model_core.js');

registerInstancePatchModel('mail.chatter', 'mail/static/src/models/chatter/chatter.js', {
    async refresh() {
        this._super(...arguments);
        this.thread.refreshMessagefailed()
        },
    toggleMessageFailedBoxVisibility() {
        this.update({ isMessageFailedBoxVisible: !this.isMessageFailedBoxVisible })
    },
    _onThreadIdOrThreadModelChanged() {
        this._super(...arguments);
        this.thread.refreshMessagefailed()
    }

});
registerFieldPatchModel('mail.chatter', 'mail/static/src/models/chatter/chatter.js', {
    isMessageFailedBoxVisible: attr({
            default: true,
    }),
});


});