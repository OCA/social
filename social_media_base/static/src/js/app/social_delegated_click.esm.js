/** @odoo-module */

import {useEffect} from "@odoo/owl";

/**
 * Bind a click on the nodes of the arch a card draws.
 *
 * A kanban card is compiled with a context of its own, where a `t-on-click`
 * cannot reach the methods of the component, so every entry the card offers
 * has its listener bound by hand. It is bound on **all** the matching nodes
 * and not on the first one found: a card with more medias than it draws has
 * two, and binding only the first left the images themselves opening the
 * publication on the social media instead of the gallery.
 *
 * Call it from `setup`: it installs a hook.
 *
 * @param {Object} rootRef ref of the root node of the card.
 * @param {String} selector CSS selector of the nodes carrying the entry.
 * @param {Function} handler what the click runs, bound to the component.
 */
export function useDelegatedClick(rootRef, selector, handler) {
    useEffect(
        (...elements) => {
            for (const element of elements) {
                element.addEventListener("click", handler);
            }
            return () => {
                for (const element of elements) {
                    element.removeEventListener("click", handler);
                }
            };
        },
        () => [...rootRef.el.querySelectorAll(selector)]
    );
}
