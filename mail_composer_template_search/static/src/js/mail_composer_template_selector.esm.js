/* Copyright 2026 Heliconia Solutions Pvt. Ltd.
   License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html). */

/* global document, setTimeout, clearTimeout */

/** @odoo-module **/

import {onMounted, onWillUnmount} from "@odoo/owl";
import {MailComposerTemplateSelector} from "@mail/core/web/mail_composer_template_selector";
import {patch} from "@web/core/utils/patch";

let searchTimeout = null;

patch(MailComposerTemplateSelector.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.searchQuery = "";
        this.state.searchTemplates = null;
        this.state.isSearching = false;
        this.state.highlightedIndex = -1;

        // Auto-focus the search input when the dropdown opens
        this._handleDropdownOpen = (ev) => {
            if (ev.target.closest(".mail-composer-template-dropdown-btn")) {
                setTimeout(() => {
                    const input = document.querySelector(".mail-template-search-input");
                    if (input) {
                        input.focus();
                    }
                }, 50);
            }
        };

        onMounted(() => {
            document.addEventListener("click", this._handleDropdownOpen, true);
        });

        onWillUnmount(() => {
            document.removeEventListener("click", this._handleDropdownOpen, true);
        });
    },

    _resetSearchState() {
        this.state.searchQuery = "";
        this.state.searchTemplates = null;
        this.state.isSearching = false;
        this.state.highlightedIndex = -1;
    },

    async onLoadTemplate(template) {
        this._resetSearchState();
        await super.onLoadTemplate(template);
    },

    get displayedTemplates() {
        if (this.state.searchQuery && this.state.searchTemplates !== null) {
            return this.state.searchTemplates;
        }
        return this.state.templates || [];
    },

    get showSearchMore() {
        if (this.state.searchQuery) {
            return false;
        }
        return (this.state.templates || []).length >= this.limit;
    },

    _applyHighlight(el) {
        const menu = el.closest(".mail-composer-template-dropdown");
        if (!menu) return;
        // Get only the insert-template DropdownItems (skip Save/Delete sections)
        const allItems = menu.querySelectorAll(":scope > .o-dropdown-item");
        const templates = this.displayedTemplates;
        // The template items are the first N items in the dropdown
        for (let i = 0; i < allItems.length && i < templates.length; i++) {
            if (i === this.state.highlightedIndex) {
                allItems[i].style.backgroundColor = "#017e84";
                allItems[i].style.color = "white";
            } else {
                allItems[i].style.backgroundColor = "";
                allItems[i].style.color = "";
            }
        }
    },

    _clearHighlight(el) {
        const menu = el.closest(".mail-composer-template-dropdown");
        if (!menu) return;
        const allItems = menu.querySelectorAll(":scope > .o-dropdown-item");
        allItems.forEach((item) => {
            item.style.backgroundColor = "";
            item.style.color = "";
        });
    },

    onSearchInput(ev) {
        const rawValue = ev.target.value;
        const query = rawValue.trim();
        this.state.searchQuery = rawValue;
        this.state.highlightedIndex = -1;
        this._clearHighlight(ev.target);

        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        if (!query) {
            this.state.searchTemplates = null;
            this.state.isSearching = false;
            return;
        }

        this.state.isSearching = true;

        searchTimeout = setTimeout(async () => {
            try {
                const fields = ["display_name"];
                const domain = [
                    ["model", "=", this.props.record.data.render_model],
                    ["name", "ilike", query],
                ];
                const results = await this.orm.searchRead(
                    "mail.template",
                    domain,
                    fields,
                    {limit: 50}
                );
                if (this.state.searchQuery.trim() === query) {
                    this.state.searchTemplates = results;
                    this.state.isSearching = false;
                }
            } catch {
                this.state.isSearching = false;
            }
        }, 300);
    },

    onSearchKeydown(ev) {
        // Stop ALL event propagation so the Dropdown component
        // does not intercept Space, Arrow keys, Enter, etc.
        ev.stopPropagation();

        const templates = this.displayedTemplates;

        if (ev.key === "ArrowDown") {
            ev.preventDefault();
            if (templates.length > 0) {
                this.state.highlightedIndex = Math.min(
                    this.state.highlightedIndex + 1,
                    templates.length - 1
                );
                // Use setTimeout to apply after OWL re-render
                setTimeout(() => this._applyHighlight(ev.target), 0);
            }
        } else if (ev.key === "ArrowUp") {
            ev.preventDefault();
            if (templates.length > 0) {
                this.state.highlightedIndex = Math.max(
                    this.state.highlightedIndex - 1,
                    0
                );
                setTimeout(() => this._applyHighlight(ev.target), 0);
            }
        } else if (ev.key === "Enter") {
            ev.preventDefault();
            const idx = this.state.highlightedIndex;
            if (idx >= 0 && idx < templates.length) {
                // Click the actual dropdown item to trigger both selection and close
                const menu = ev.target.closest(".mail-composer-template-dropdown");
                if (menu) {
                    const items = menu.querySelectorAll(":scope > .o-dropdown-item");
                    if (items[idx]) {
                        items[idx].click();
                    }
                }
            }
        }
    },
});
