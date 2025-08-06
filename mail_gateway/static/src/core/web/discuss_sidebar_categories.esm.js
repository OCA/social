// Import {discussSidebarCategoriesRegistry} from "@mail/discuss/core/web/discuss_sidebar_categories";
//
// discussSidebarCategoriesRegistry.add(
//     "gateway",
//     {
//         predicate: (store) => {
//             store.discuss.gateway.threads.some(
//                 (thread) => thread?.displayToSelf || thread?.isLocallyPinned
//             );
//         },
//         value: (store) => store.discuss.gateway,
//     },
//     {sequence: 30}
// );
// import { DiscussSidebarCategory } from "@mail/discuss/core/public_web/discuss_sidebar_categories";
// import { patch } from "@web/core/utils/patch";
//
// patch(DiscussSidebarCategory.prototype, {
//     get actions() {
//         const actions = super.actions;
//         if (this.category.livechatChannel && this.category.open) {
//
//         }
//         return actions;
//     },
// });
