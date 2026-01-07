# Copyright (C) 2024 - KMEE
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

import logging
import re

import lxml.html

from odoo import models
from odoo.tools import ustr

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _get_inline_attachment_ids(self):
        """Identifica IDs de anexos que são referenciados inline no body.

        Retorna um set com os IDs dos anexos que aparecem como imagens
        inline no body da mensagem (referências /web/image/{id}).
        """
        self.ensure_one()
        inline_attachment_ids = set()

        if not self.body:
            return inline_attachment_ids

        try:
            root = lxml.html.fromstring(ustr(self.body))
            for node in root.iter("img"):
                src = node.get("src", "")
                # Pattern matches:
                # - /web/image/{id}
                # - /web/image/{id}?access_token=...
                # - /web/image/{id}/...
                matches = re.findall(r"/web/image/(\d+)", src)
                for mid in matches:
                    inline_attachment_ids.add(int(mid))
        except Exception as e:
            _logger.warning(
                "Erro ao processar body para detectar anexos inline "
                "na mensagem %d: %s",
                self.id,
                e,
            )

        return inline_attachment_ids

    def _message_format(self, fnames, format_reply=True, legacy=False):
        """Override para filtrar anexos inline do campo attachment_ids.

        Anexos que são referenciados inline no body (imagens) não devem
        aparecer na lista de anexos do mail.message.
        """
        vals_list = super()._message_format(
            fnames, format_reply=format_reply, legacy=legacy
        )

        # Processa em batch para melhor performance
        message_ids = [vals["id"] for vals in vals_list]
        messages = self.browse(message_ids)

        for vals in vals_list:
            message_id = vals["id"]
            message = messages.filtered(lambda m, mid=message_id: m.id == mid)
            if not message:
                continue

            inline_attachment_ids = message._get_inline_attachment_ids()

            if inline_attachment_ids and vals.get("attachment_ids"):
                # Filtra anexos inline da lista de anexos formatados
                filtered_attachments = [
                    att
                    for att in vals["attachment_ids"]
                    if att.get("id") not in inline_attachment_ids
                ]
                vals["attachment_ids"] = filtered_attachments
                _logger.debug(
                    "Filtrados %d anexos inline da mensagem %d "
                    "(IDs: %s). Restaram %d anexos.",
                    len(inline_attachment_ids),
                    message.id,
                    sorted(inline_attachment_ids),
                    len(filtered_attachments),
                )

        return vals_list
