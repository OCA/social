import {SuggestionService} from "@mail/core/common/suggestion_service";
import {patch} from "@web/core/utils/patch";

patch(SuggestionService.prototype, {
    getPartnerSuggestions(thread) {
        const partners = super.getPartnerSuggestions(thread);
        if (thread?.model === "discuss.channel") {
            return partners;
        }
        return [...partners].filter((persona) => persona.is_suggestion === true);
    },
});
