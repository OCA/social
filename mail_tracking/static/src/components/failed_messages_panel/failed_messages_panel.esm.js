import {ActionPanel} from "@mail/discuss/core/common/action_panel";
import {MessageCardList} from "@mail/core/common/message_card_list";
import {_t} from "@web/core/l10n/translation";
import {useFailedMessageSearch} from "@mail_tracking/core/search/failed_message_search_hook.esm";

const {Component, onWillUpdateProps, useState} = owl;

export class FailedMessagesPanel extends Component {
    static components = {
        MessageCardList,
        ActionPanel,
    };
    static props = ["thread", "className?", "closeSearch?", "onClickJump?"];
    static template = "mail_tracking.FailedMessagesPanel";

    setup() {
        this.state = useState({searchTerm: "", searchedTerm: ""});
        this.messageSearch = useFailedMessageSearch(this.props.thread);
        onWillUpdateProps((nextProps) => {
            if (this.props.thread.notEq(nextProps.thread)) {
                this.env.searchMenu?.close();
            }
        });
        this.search_failed();
    }
    get title() {
        return _t("Failed messages");
    }
    get MESSAGES_FOUND() {
        if (this.messageSearch.messages.length === 0) {
            return false;
        }
        return _t("%s failed messages found", this.messageSearch.count);
    }
    search_failed() {
        this.messageSearch.filter_failed();
    }
    clear() {
        this.messageSearch.clear();
    }
    onLoadMoreVisible() {
        const before = this.messageSearch.messages
            ? Math.min(...this.messageSearch.messages.map((message) => message.id))
            : false;
        this.messageSearch.search(before);
    }
}
