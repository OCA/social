/* @odoo-module */

import {discussSidebarCategoriesRegistry} from "@mail/discuss/core/web/discuss_sidebar_categories";

discussSidebarCategoriesRegistry.add(
    "gateway",
    {
        predicate: (store) => {
            store.discuss.gateway.threads.some(
                (thread) => thread?.displayToSelf || thread?.isLocallyPinned
            );
        },
        value: (store) => store.discuss.gateway,
    },
    {sequence: 30}
);
