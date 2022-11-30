odoo.define("mail_broker.Broker", function (require) {
    "use strict";
    var BasicComposer = require("mail.composer.Basic");
    var ExtendedComposer = require("mail.composer.Extended");
    var core = require("web.core");
    var AbstractAction = require("web.AbstractAction");
    // Var ControlPanelMixin = require("web.ControlPanelMixin");
    var ThreadWidget = require("mail.widget.Thread");
    var dom = require("web.dom");

    var QWeb = core.qweb;
    var _t = core._t;

    var Broker = AbstractAction.extend({
        contentTemplate: "mail_broker.broker",
        events: {
            "click .o_mail_channel_settings": "_onChannelSettingsClicked",
            "click .o_mail_discuss_item": "_onSelectBrokerChannel",
            "click .o_mail_sidebar_title .o_add": "_onSearchThread",
            "blur .o_mail_add_thread input": "_onSearchThreadBlur",
        },
        init: function (parent, action, options) {
            this._super.apply(this, arguments);
            this.action = action;
            this.action_manager = parent;
            this.domain = [];
            this.options = options || {};
            this._threadsScrolltop = {};
            this._composerStates = {};
            this._defaultChatID =
                this.options.active_id ||
                this.action.context.active_id ||
                this.action.params.default_active_id;
            this._selectedMessage = null;
        },

        /**
         * @override
         */
        on_attach_callback: function () {
            if (this._thread) {
                this._threadWidget.scrollToPosition(
                    this._threadsScrolltop[this._thread.getID()]
                );
                this._loadEnoughMessages();
            }
        },

        /**
         * @override
         */
        on_detach_callback: function () {
            if (this._thread) {
                this._threadsScrolltop[
                    this._thread.getID()
                ] = this._threadWidget.getScrolltop();
            }
        },
        start: function () {
            var self = this;

            return this._super.apply(this, arguments).then(function () {
                return self._initRender();
            });
            /*
            Return this.alive($.when.apply($, defs))
                .then(function() {
                    if (self._defaultChatID) {
                        return self.alive(self._setThread(self._defaultChatID));
                    }
                })

                .then(function() {
                    self._updateThreads();
                    self._startListening();
                    self._threadWidget.$el.on(
                        "scroll",
                        null,
                        _.debounce(function() {
                            var $noContent = self._threadWidget.$(".o_mail_no_content");
                            if (
                                self._threadWidget.getScrolltop() < 20 &&
                                !self._thread.isAllHistoryLoaded() &&
                                !$noContent.length
                            ) {
                                self._loadMoreMessages();
                            }
                            if (self._threadWidget.isAtBottom()) {
                                self._thread.markAsRead();
                            }
                        }, 100)
                    );
                });
            */
        },
        _initRender: function () {
            var self = this;
            this._basicComposer = new BasicComposer(this, {
                mentionPartnersRestricted: true,
            });
            this._extendedComposer = new ExtendedComposer(this, {
                mentionPartnersRestricted: true,
            });
            this._basicComposer
                .on("post_message", this, this._onPostMessage)
                .on("input_focused", this, this._onComposerFocused);
            this._extendedComposer
                .on("post_message", this, this._onPostMessage)
                .on("input_focused", this, this._onComposerFocused);
            this._renderButtons();

            var defs = [];

            defs.push(this._renderThread());
            defs.push(this._basicComposer.appendTo(this.$(".o_mail_discuss_content")));
            return Promise.all(defs)
                .then(function () {
                    if (self._defaultChatID) {
                        return self._setThread(self._defaultChatID);
                    }
                })

                .then(function () {
                    self._updateThreads();
                    self._startListening();
                    self._threadWidget.$el.on(
                        "scroll",
                        null,
                        _.debounce(function () {
                            var $noContent = self._threadWidget.$(".o_mail_no_content");
                            if (
                                self._threadWidget.getScrolltop() < 20 &&
                                !self._thread.isAllHistoryLoaded() &&
                                !$noContent.length
                            ) {
                                self._loadMoreMessages();
                            }
                            if (self._threadWidget.isAtBottom()) {
                                self._thread.markAsRead();
                            }
                        }, 100)
                    );
                });
        },
        _startListening: function () {
            this.call("mail_service", "getMailBus").on(
                "new_message",
                this,
                this._onNewMessage
            );
        },
        _setThread: function (threadID) {
            this._storeThreadState();
            var thread = this.call("mail_service", "getThread", threadID);
            if (!thread) {
                return;
            }
            this._thread = thread;

            var self = this;
            this.messagesSeparatorPosition = undefined;
            return this._fetchAndRenderThread().then(function () {
                self._thread.markAsRead();
                // Restore scroll position and composer of the new
                // current thread
                self._restoreThreadState();

                // Update control panel before focusing the composer, otherwise
                // focus is on the searchview
                self.set("title", self._thread.getTitle());

                self.action_manager.do_push_state({
                    action: self.action.id,
                    active_id: self._thread.getID(),
                });
            });
        },
        _storeThreadState: function () {
            if (this._thread) {
                this._threadsScrolltop[
                    this._thread.getID()
                ] = this._threadWidget.getScrolltop();
            }
        },
        _loadEnoughMessages: function () {
            var $el = this._threadWidget.el;
            var loadMoreMessages =
                $el.clientHeight &&
                $el.clientHeight === $el.scrollHeight &&
                !this._thread.isAllHistoryLoaded();
            if (loadMoreMessages) {
                return this._loadMoreMessages().then(
                    this._loadEnoughMessages.bind(this)
                );
            }
        },
        _getThreadRenderingOptions: function () {
            if (_.isUndefined(this.messagesSeparatorPosition)) {
                if (this._unreadCounter) {
                    var messageID = this._thread.getLastSeenMessageID();
                    this.messagesSeparatorPosition = messageID || "top";
                } else {
                    // No unread message -> don't display separator
                    this.messagesSeparatorPosition = false;
                }
            }
            return {
                displayLoadMore: !this._thread.isAllHistoryLoaded(),
                squashCloseMessages: true,
                messagesSeparatorPosition: this.messagesSeparatorPosition,
                displayEmailIcons: false,
                displayReplyIcons: false,
                displayBottomThreadFreeSpace: true,
                displayModerationCommands: false,
                displayMarkAsRead: false,
                displayDocumentLinks: false,
                displayStars: false,
            };
        },
        _fetchAndRenderThread: function () {
            var self = this;
            return this._thread.fetchMessages().then(function () {
                self._threadWidget.render(
                    self._thread,
                    self._getThreadRenderingOptions()
                );
                return self._loadEnoughMessages();
            });
        },
        _renderButtons: function () {
            // This is a hook just in case some buttons are required
        },
        _renderThread: function () {
            this._threadWidget = new ThreadWidget(this, {
                areMessageAttachmentsDeletable: false,
                loadMoreOnScroll: true,
            });
            this._threadWidget.on("load_more_messages", this, this._loadMoreMessages);
            return this._threadWidget.appendTo(this.$(".o_mail_discuss_content"));
        },
        _renderSidebar: function (options) {
            var $sidebar = $(
                QWeb.render("mail_broker.broker.Sidebar", {
                    activeThreadID: this._thread ? this._thread.getID() : undefined,
                    bots: options.bots,
                })
            );
            return $sidebar;
        },
        _restoreThreadState: function () {
            var $newMessagesSeparator = this.$(".o_thread_new_messages_separator");
            if ($newMessagesSeparator.length) {
                this._threadWidget.$el.scrollTo($newMessagesSeparator);
            } else {
                var newThreadScrolltop = this._threadsScrolltop[this._thread.getID()];
                this._threadWidget.scrollToPosition(newThreadScrolltop);
            }
        },
        _updateThreads: function () {
            var bots = this.call("mail_service", "getBrokerBots");
            var $sidebar = this._renderSidebar({
                bots: bots,
            });
            this.$(".o_mail_discuss_sidebar").html($sidebar.contents());
            var self = this;
            _.each(bots, function (bot, broker_id) {
                var $input = self.$(
                    ".o_mail_add_thread[data-bot=" + broker_id + "] input"
                );
                self._prepareAddThreadInput($input, broker_id, bot);
            });
        },
        _prepareAddThreadInput: function ($input, broker_id) {
            var self = this;
            $input.autocomplete({
                source: function (request, response) {
                    self._lastSearchVal = _.escape(request.term);
                    self._searchChannel(broker_id, self._lastSearchVal).then(function (
                        result
                    ) {
                        response(result);
                    });
                },
                select: function (ev, ui) {
                    self._setThread("broker_thread_" + ui.item.id);
                    self._updateThreads();
                },
                focus: function (ev) {
                    ev.preventDefault();
                },
                html: true,
            });
        },
        _loadMoreMessages: function () {
            var self = this;
            var oldestMessageID = this.$(".o_thread_message").first().data("messageId");
            var oldestMessageSelector =
                '.o_thread_message[data-message-id="' + oldestMessageID + '"]';
            var offset = -dom.getPosition(document.querySelector(oldestMessageSelector))
                .top;
            return this._thread.fetchMessages({loadMore: true}).then(function () {
                if (self.messagesSeparatorPosition === "top") {
                    // Reset value to re-compute separator position
                    self.messagesSeparatorPosition = undefined;
                }
                self._threadWidget.render(
                    self._thread,
                    self._getThreadRenderingOptions()
                );
                offset += dom.getPosition(document.querySelector(oldestMessageSelector))
                    .top;
                self._threadWidget.scrollToPosition(offset);
            });
        },
        _onSearchThread: function (ev) {
            ev.preventDefault();
            var bot = $(ev.target).data("bot");
            this.$(".o_mail_add_thread[data-bot=" + bot + "]")
                .show()
                .find("input")
                .focus();
        },
        _onSearchThreadBlur: function () {
            this.$(".o_mail_add_thread").hide();
        },
        _onChannelSettingsClicked: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var threadID = $(ev.target).data("thread-id");
            var thread = this.call("mail_service", "getThread", threadID);
            this.do_action({
                type: "ir.actions.act_window",
                res_model: "mail.broker.channel",
                res_id: thread.resId,
                name: _t("Configure chat"),
                views: [[false, "form"]],
                target: "new",
            });
        },
        _onNewMessage: function (message) {
            var thread_id = "broker_thread_" + message.broker_channel_id;
            if (this._thread && thread_id === this._thread.getID()) {
                this._thread.markAsRead();
                var shouldScroll = this._threadWidget.isAtBottom();
                var self = this;
                this._fetchAndRenderThread().then(function () {
                    if (shouldScroll) {
                        self._threadWidget.scrollToMessage({
                            msgID: message.getID(),
                        });
                    }
                });
            }
            // Re-render sidebar to indicate that there is a new message in
            // The corresponding threads
            this._updateThreads();
            // Dump scroll position of threads in which the new message arrived
            this._threadsScrolltop = _.omit(
                this._threadsScrolltop,
                message.getThreadIDs()
            );
        },
        _searchChannel: function (broker_id, searchVal) {
            return this._rpc({
                model: "mail.broker",
                method: "channel_search",
                args: [[parseInt(broker_id, 10)], searchVal],
            }).then(function (result) {
                var values = [];
                _.each(result, function (channel) {
                    var escapedName = _.escape(channel.name);
                    values.push(
                        _.extend(channel, {
                            value: escapedName,
                            label: escapedName,
                        })
                    );
                });
                return values;
            });
        },
        _onComposerFocused: function () {
            // Hook
        },
        _onSelectBrokerChannel: function (ev) {
            ev.preventDefault();
            var threadID = $(ev.currentTarget).data("thread-id");
            this._setThread(threadID);
            this._updateThreads();
        },
        _onPostMessage: function (messageData) {
            var self = this;
            var options = {};
            if (this._selectedMessage) {
                messageData.subtype = this._selectedMessage.isNote()
                    ? "mail.mt_note"
                    : "mail.mt_comment";
                messageData.subtype_id = false;
                messageData.broker_type = "comment";

                options.documentID = this._selectedMessage.getDocumentID();
                options.documentModel = this._selectedMessage.getDocumentModel();
            }
            this._thread
                .postMessage(messageData, options)
                .then(function () {
                    if (self._selectedMessage) {
                        self._renderSnackbar(
                            "mail.discuss.MessageSentSnackbar",
                            {
                                documentName: self._selectedMessage.getDocumentName(),
                            },
                            5000
                        );
                        self._unselectMessage();
                    } else {
                        self._threadWidget.scrollToBottom();
                    }
                })
                .catch(function () {
                    // TODO: Display notifications
                });
        },
    });

    core.action_registry.add("mail.broker", Broker);

    return Broker;
});
