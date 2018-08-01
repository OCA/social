# Copyright 2018 Eficent Business and IT Consulting Services S.L.
# Copyright 2018 Odoo, S.A.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from openerp.addons.mail.wizard.mail_compose_message import MailComposer


def post_load_hook():
    """
    We need this hook only in v9 in order to be able to capture the subtype.

    """
    def new_send_mail(self, auto_commit=False):

        if 'subtype_id' not in self._fields:
            return self.send_mail_original(auto_commit=auto_commit)

        """ Process the wizard content and proceed with sending the related
                    email(s), rendering any template patterns on the fly 
                    if needed. """
        for wizard in self:
            # Duplicate attachments linked to the email.template.
            # Indeed, basic mail.compose.message wizard duplicates
            # attachments in mass
            # mailing mode. But in 'single post' mode, attachments of
            # an email template
            # also have to be duplicated to avoid changing their ownership.
            if wizard.attachment_ids and \
                    wizard.composition_mode != 'mass_mail' and \
                    wizard.template_id:
                new_attachment_ids = []
                for attachment in wizard.attachment_ids:
                    if attachment in wizard.template_id.attachment_ids:
                        new_attachment_ids.append(attachment.copy(
                            {'res_model': 'mail.compose.message',
                             'res_id': wizard.id}).id)
                    else:
                        new_attachment_ids.append(attachment.id)
                    wizard.write({'attachment_ids': [(6, 0,
                                                      new_attachment_ids)]})

            # Mass Mailing
            mass_mode = wizard.composition_mode in ('mass_mail', 'mass_post')

            Mail = self.env['mail.mail']
            ActiveModel = self.env[
                wizard.model if wizard.model else 'mail.thread']
            if wizard.template_id:
                # template user_signature is added when generating body_html
                # mass mailing: use template auto_delete value -> note,
                # for emails mass mailing only
                Mail = Mail.with_context(mail_notify_user_signature=False)
                ActiveModel = ActiveModel.with_context(
                    mail_notify_user_signature=False,
                    mail_auto_delete=wizard.template_id.auto_delete)
            if not hasattr(ActiveModel, 'message_post'):
                ActiveModel = self.env['mail.thread'].with_context(
                    thread_model=wizard.model)
            if wizard.composition_mode == 'mass_post':
                # do not send emails directly but use the queue instead
                # add context key to avoid subscribing the author
                ActiveModel = ActiveModel.with_context(
                    mail_notify_force_send=False,
                    mail_create_nosubscribe=True)
            # wizard works in batch mode: [res_id] or
            # active_ids or active_domain
            if mass_mode and wizard.use_active_domain and wizard.model:
                res_ids = self.env[wizard.model].search(
                    eval(wizard.active_domain)).ids
            elif mass_mode and wizard.model and self._context.get(
                    'active_ids'):
                res_ids = self._context['active_ids']
            else:
                res_ids = [wizard.res_id]

            batch_size = int(self.env['ir.config_parameter'].sudo().get_param(
                'mail.batch_size')) or self._batch_size
            sliced_res_ids = [res_ids[i:i + batch_size] for i in
                              range(0, len(res_ids), batch_size)]

            # ----  START OF PATCH
            if wizard.composition_mode == 'mass_mail' or wizard.is_log or (
                    wizard.composition_mode == 'mass_post'
                    and not wizard.notify):  # log a note: subtype is False
                subtype_id = False
            elif wizard.subtype_id:
                subtype_id = wizard.subtype_id
            else:
                subtype_id = self.sudo().env.ref('mail.mt_comment',
                                                 raise_if_not_found=False)
            if subtype_id:
                external_subtype = subtype_id.get_external_id()
                if external_subtype:
                    subtype = external_subtype[subtype_id.id]
            else:
                subtype = 'mail.mt_comment'
            # ----  END OF PATCH

            for res_ids in sliced_res_ids:
                batch_mails = Mail
                all_mail_values = wizard.get_mail_values(res_ids)
                for res_id, mail_values in all_mail_values.iteritems():
                    if wizard.composition_mode == 'mass_mail':
                        batch_mails |= Mail.create(mail_values)
                    else:
                        # subtype = 'mail.mt_comment' -> Removed
                        if wizard.is_log or (
                                wizard.composition_mode == 'mass_post'
                                and not wizard.notify):  # log a note:
                            # subtype is False
                            subtype = False
                        ActiveModel.browse(res_id).message_post(
                            message_type='comment', subtype=subtype,
                            **mail_values)

                if wizard.composition_mode == 'mass_mail':
                    batch_mails.send(auto_commit=auto_commit)

        return {'type': 'ir.actions.act_window_close'}

    if not hasattr(MailComposer, 'send_mail_original'):
        MailComposer.send_mail_original = MailComposer.send_mail

    MailComposer.send_mail = new_send_mail
