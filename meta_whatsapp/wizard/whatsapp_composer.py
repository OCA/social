from odoo import _, api, fields, models
from odoo.tools.safe_eval import safe_eval


class WhatsAppComposer(models.TransientModel):
    _name = "whatsapp.composer"
    _description = "Send WhatsApp Wizard"

    res_model = fields.Char("Model", required=True)
    res_ids = fields.Char("Document IDs", required=True)

    template_id = fields.Many2one("whatsapp.template", string="Template", required=True)
    phone = fields.Char(
        string="Phone Number", compute="_compute_phone", store=True, readonly=False
    )
    body = fields.Text(
        string="Message Preview", compute="_compute_body", store=True, readonly=False
    )

    @api.depends("res_model", "res_ids")
    def _compute_phone(self):
        for record in self:
            if record.res_model and record.res_ids:
                res_ids = safe_eval(record.res_ids)
                if isinstance(res_ids, int):
                    res_ids = [res_ids]

                # Simple logic to find phone/mobile field
                docs = self.env[record.res_model].browse(res_ids)
                if docs:
                    record.phone = getattr(
                        docs[0], "mobile", getattr(docs[0], "phone", False)
                    )

    @api.depends("template_id")
    def _compute_body(self):
        for record in self:
            if record.template_id:
                record.body = record.template_id.body

    def action_send_whatsapp(self):
        self.ensure_one()
        res_ids = safe_eval(self.res_ids)
        if isinstance(res_ids, int):
            res_ids = [res_ids]

        active_ids = self.env[self.res_model].browse(res_ids)

        messages = []
        for doc in active_ids:
            # Logic to resolve phone number
            phone = getattr(doc, "mobile", getattr(doc, "phone", False))
            if not phone:
                continue

            # Create message record
            # In a real implementation, we would render variables here
            msg = self.env["whatsapp.message"].create(
                {
                    "body": self.body,
                    "mobile_number": phone,
                    "partner_id": doc.id if self.res_model == "res.partner" else False,
                    "template_id": self.template_id.id,
                    "res_model": self.res_model,
                    "res_id": doc.id,
                    "status": "draft",
                }
            )
            messages.append(msg)

        # Send immediately for now
        for msg in messages:
            msg.action_send()

            # Post message to chatter if the model supports it
            if msg.res_model and msg.res_id:
                record = self.env[msg.res_model].browse(msg.res_id)
                if hasattr(record, "message_post"):
                    # Use the body from the message record which is now rendered
                    body = _("<b>WhatsApp Message Sent</b><br/>%s") % msg.body
                    record.message_post(body=body)

        return {"type": "ir.actions.act_window_close"}
