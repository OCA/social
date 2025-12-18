import logging
from datetime import datetime, timedelta

from odoo import fields, models
from odoo.exceptions import ValidationError

from ..social_facebook_utils import _URL_GRAPH_FACEBOOK

_logger = logging.getLogger(__name__)


class WizardFacebookSystemUser(models.TransientModel):
    _name = "wizard.facebook.system.user"
    _description = "Wizard for entering system user token"

    system_user_token = fields.Char()

    def action_connect_system_user(self):
        """Connect pages using the System User token"""
        token = self.system_user_token
        if not token:
            raise ValidationError(self.env._("System User Token is required"))
        # active_id = self.env.context.get("active_id")
        # media = self.env["social.media"].browse(active_id)

        try:
            import requests

            r = requests.get(
                f"{_URL_GRAPH_FACEBOOK}/me", params={"access_token": token}, timeout=8
            )
            r.raise_for_status()
        except Exception as e:
            _logger.error(f"Error validating system user token: {e}")
            raise ValidationError(
                self.env._("Invalid System User Token or network error.")
            ) from e

        pages = []
        try:
            pages = get_pages_from_facebook(token)
        except Exception as e:
            raise ValidationError(
                self.env._(
                    "Failed to fetch pages using the provided " "System User Token."
                )
            ) from e

        if not pages:
            raise ValidationError(
                self.env._(
                    "No Facebook pages found for the provided " "System User Token."
                )
            )

        created = []
        updated = []
        failed = []

        # safe get media reference
        media_ref = self.env.ref(
            "social_media_facebook.social_media_facebook", raise_if_not_found=False
        )
        media_id = media_ref.id if media_ref else False

        token_expires_at = datetime.now() + timedelta(days=365 * 10)

        for page in pages:
            page_id = page.get("id")
            page_name = page.get("name")
            page_token = page.get("access_token") or token
            try:
                with self.env.cr.savepoint():
                    exiting = self.env["social.account"].search(
                        [
                            ("page_id", "=", page_id),
                            ("media_id", "=", media_id),
                        ],
                        limit=1,
                    )

                    vals = {
                        "name": page_name,
                        "username": page_name,
                        "page_id": page_id,
                        "page_name": page_name,
                        "page_access_token": page_token,
                        "facebook_user_token": token,
                        "access_token": page_token,
                        "token_expires_at": token_expires_at,
                        "status": "active",
                        "media_id": media_id,
                    }

                    try:
                        pic = self.env[
                            "social.account"
                        ]._download_facebook_page_picture(page_id, page_token)
                        if pic:
                            vals["image_1920"] = pic
                    except Exception as e:
                        _logger.warning(
                            f"Failed to download profile picture for page {page_name} "
                            f"(ID: {page_id}): {e}"
                        )

                    if token:
                        vals["facebook_system_user_token"] = token
                        vals["facebook_app_id"] = False
                        vals["facebook_app_secret"] = False

                    if exiting:
                        exiting.write(vals)
                        updated.append(exiting.id)
                    else:
                        new = self.env["social.account"].create(vals)
                        created.append(new.id)
            except Exception as e:
                _logger.error(
                    f"Failed to create/update account for page {page_name} "
                    f"(ID: {page_id}): {e}"
                )
                failed.append({"page_id": page_id, "error": str(e)})
        try:
            key = "social_media_base.facebook_system_user_token"
            self.env["ir.config_parameter"].sudo().set_param(key, token)
            self.env["ir.config_parameter"].sudo().set_param(
                "social_media_base.facebook_connection_method", "system_user"
            )
        except Exception as e:
            _logger.error(f"Failed to save system user token to config parameters: {e}")

        if failed:
            msg = self.env._(
                f"Created : {len(created)}, Updated : {len(updated)}, "
                f"Failed : {len(failed)} accounts."
            )
            raise ValidationError(msg)

        return {"type": "ir.actions.act_window_close"}


def get_pages_from_facebook(system_user_token):
    """Fetch pages using the system user token from Facebook API"""
    import requests
    from requests.adapters import HTTPAdapter, Retry

    url = f"{_URL_GRAPH_FACEBOOK}/me/accounts"
    params = {
        "access_token": system_user_token,
    }
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    try:
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        _logger.error(f"Error fetching pages from Facebook: {e}")
        raise

    pages = []
    for p in data.get("data", []):
        pages.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "access_token": p.get("access_token"),
            }
        )
    return pages
