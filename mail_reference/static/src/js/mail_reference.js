//Copyright 2019 Therp BV <https://therp.nl>
//License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
odoo.define('mail_reference.basic_composer', function(require) {

    var BasicComposer = require('mail.composer').BasicComposer;
    var data = require('web.data');
    var Model = require('web.Model');
    var ajax = require('web.ajax');

    BasicComposer.include({
        
        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.register_custom_mentions();
        },

        /**
         * Called when the user enters a character after the delimitor and for
         * every delimitor. 
         *
         * Performs a search_read on the model defined on `this.model` and
         * searches for the records based on their `name` field.
         *
         * */
        mention_execute_action: function (mention_word) {
            domain = [
                ['name', 'ilike', mention_word],
            ]
            fields = ['id', 'name']
            return this.mention_fetch_throttled(
                new Model(this.context.shows_model_id_name),
                'search_read',
                {domain: domain, fields: fields, limit: 8}).then(
                    function (result) {
                        return result
            })
        },

        /**
         * Called when the user clicks `New message` or `Log an internal note`
         * and it's purpose is to see which delimiters are supported for this
         * model and at which model do they point to.
         *
         * */
        register_custom_mentions: function () {
            var self = this;
            var query = new data.Query(
                new Model(
                    'mail.reference.mention',
                    {},
                    [['model_names', 'like', this.context.default_model]]),
                ['delimiter', 'shows_model_id_name'],
            );
            query.all().then(function (res) {
                res.forEach(function (mention) {
                    self.context.shows_model_id_name =
                        mention.shows_model_id_name
                    self.mention_manager.register({
                        delimiter: mention.delimiter,
                        generate_links: true,
                        model: mention.shows_model_id_name,
                        fetch_callback: self.mention_execute_action.bind(self),
                        suggestion_template: 'mail.MentionChannelSuggestions',
                    });
                });
            });
        }

    });
});
