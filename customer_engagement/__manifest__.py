{
    "name": "Customer Engagement",
    "version": "18.0.2.0.0",
    "category": "Services",
    "summary": "Omnichannel Customer Engagement Center",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "depends": [
        "mail",
        "contacts",
        "bus",
    ],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "data/conversation_stage_data.xml",
        "data/engage_folder_data.xml",
        "data/canned_response_data.xml",
        "data/ir_cron_data.xml",
        "views/conversation_stage_views.xml",
        "views/conversation_label_views.xml",
        "views/engage_team_views.xml",
        "views/engage_folder_views.xml",
        "views/canned_response_views.xml",
        "views/conversation_views.xml",
        "views/api_key_views.xml",
        "views/res_partner_views.xml",
        "views/res_users_views.xml",
        "views/sla_policy_views.xml",
        "views/routing_rule_views.xml",
        "views/automation_views.xml",
        "views/metrics_views.xml",
        "views/csat_views.xml",
        "views/csat_templates.xml",
        "views/integration_views.xml",
        "wizard/transfer_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # SCSS - Component styles (self-contained, no imports)
            "customer_engagement/static/src/scss/components/_sidebar.scss",
            "customer_engagement/static/src/scss/components/_conversation_list.scss",
            "customer_engagement/static/src/scss/components/_chat_panel.scss",
            "customer_engagement/static/src/scss/components/_message_bubbles.scss",
            "customer_engagement/static/src/scss/components/_composer.scss",
            "customer_engagement/static/src/scss/components/_contact_panel.scss",
            "customer_engagement/static/src/scss/components/_responsive.scss",
            # SCSS - Main styles
            "customer_engagement/static/src/scss/inbox.scss",
            # JavaScript - Sidebar components
            "customer_engagement/static/src/js/components/sidebar/sidebar_item.js",
            "customer_engagement/static/src/js/components/sidebar/sidebar_section.js",
            "customer_engagement/static/src/js/components/sidebar/engage_sidebar.js",
            # JavaScript - Conversation List components
            "customer_engagement/static/src/js/components/conversation_list/channel_badge.js",
            "customer_engagement/static/src/js/components/conversation_list/label_pills.js",
            "customer_engagement/static/src/js/components/conversation_list/priority_indicator.js",  # noqa: B950
            "customer_engagement/static/src/js/components/conversation_list/relative_time.js",
            "customer_engagement/static/src/js/components/conversation_list/conversation_card.js",  # noqa: B950
            "customer_engagement/static/src/js/components/conversation_list/conversation_list.js",  # noqa: B950
            # JavaScript - Chat Panel components
            "customer_engagement/static/src/js/components/chat_panel/timeline_event.js",
            "customer_engagement/static/src/js/components/chat_panel/message_bubble.js",
            "customer_engagement/static/src/js/components/chat_panel/note_bubble.js",
            "customer_engagement/static/src/js/components/chat_panel/message_list.js",
            "customer_engagement/static/src/js/components/chat_panel/emoji_picker.js",
            "customer_engagement/static/src/js/components/chat_panel/canned_response_picker.js",
            "customer_engagement/static/src/js/components/chat_panel/attachment_uploader.js",
            "customer_engagement/static/src/js/components/chat_panel/rich_composer.js",
            "customer_engagement/static/src/js/components/chat_panel/chat_header.js",
            "customer_engagement/static/src/js/components/chat_panel/chat_panel.js",
            # JavaScript - Contact Panel components
            "customer_engagement/static/src/js/components/contact_panel/contact_panel.js",
            # JavaScript - Main inbox action
            "customer_engagement/static/src/js/inbox_action.js",
            # XML Templates
            "customer_engagement/static/src/xml/components/sidebar_templates.xml",
            "customer_engagement/static/src/xml/components/conversation_list_templates.xml",
            "customer_engagement/static/src/xml/components/chat_panel_templates.xml",
            "customer_engagement/static/src/xml/components/contact_panel_templates.xml",
            "customer_engagement/static/src/xml/inbox_templates.xml",
        ],
    },
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
