<?xml version="1.0" encoding="utf-8" ?>
<odoo>
    <record id="res_config_settings_view_form" model="ir.ui.view">
        <field
            name="name"
        >res.config.settings.view.form.inherit.mail.show.follower</field>
        <field name="model">res.config.settings</field>
        <field name="inherit_id" ref="mail.res_config_settings_view_form" />
        <field name="arch" type="xml">
            <block id="emails" position="inside">
                <setting id="mailer_follower_options">
                    <div class="content-group">
                        <div>
                            <label
                                for="show_internal_users_cc"
                                string="Show Followers on mails"
                            />
                            <div class="mt8">
                                <field name="show_internal_users_cc" class="w-auto" />
                                <label
                                    for="show_internal_users_cc"
                                    class="o_light_label"
                                    string="Show Internal Users on CC"
                                />
                            </div>
                            <div class="mt8">
                                <label for="show_followers_message_sent_to" />
                                <field
                                    name="show_followers_message_sent_to"
                                    placeholder="This message has been sent to"
                                    class="w-100"
                                />
                            </div>
                            <div class="row mt8">
                                <label
                                    for="show_followers_partner_format"
                                    class="col-lg-4"
                                />
                                <field
                                    name="show_followers_partner_format"
                                    placeholder="%%(partner_name)s &lt;%%(partner_email)s&gt;"
                                />
                                <div class="text-muted">
                                    <strong>Supported parameters:</strong>
                                    <div>%%(partner_name)s = Partner Name</div>
                                    <div>%%(partner_email)s = Partner Email</div>
                                    <div
                                    >%%(partner_email_domain)s = Partner Email Domain</div>
                                </div>
                            </div>
                            <div class="mt8">
                                <label for="show_followers_message_response_warning" />
                                <field
                                    name="show_followers_message_response_warning"
                                    placeholder="Notice: Replies to this email will be sent to all recipients."
                                    class="w-100"
                                />
                            </div>
                            <div class="mt8">
                                <label
                                    for="show_followers_models_to_exclude"
                                    string="Models to exclude"
                                    class="o_light_label"
                                />
                                <field
                                    name="show_followers_models_to_exclude"
                                    placeholder="blog.blog,blog.post"
                                    class="w-100"
                                />
                            </div>
                        </div>
                        <div class="mt8">
                            <label
                                for="show_followers_message_preview"
                                class="text-muted"
                            />
                            <field
                                name="show_followers_message_preview"
                                widget="html"
                                class="w-100"
                            />
                        </div>
                    </div>
                </setting>
            </block>
        </field>
    </record>
</odoo>
