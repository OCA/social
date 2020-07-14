from odoo import api, models, registry
from odoo import SUPERUSER_ID
from odoo.http import request

# TODO: This is a dirty hack which renders all image_small of res_partner public! It's needed for the icon of the push notification.
# TODO: Maybe in the future add an access_token or verify if the request comes from FCM
class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def binary_content(cls, xmlid=None, model='ir.attachment', id=None, field='datas',
                       unique=False, filename=None, filename_field='datas_fname', download=False,
                       mimetype=None, default_mimetype='application/octet-stream',
                       access_token=None, related_id=None, access_mode=None, env=None):
        env = env or request.env

        if model == 'res.partner' and field == 'image_small':
            env = env(user=SUPERUSER_ID)
        return super(Http, cls).binary_content(
            xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            default_mimetype=default_mimetype, access_token=access_token, related_id=related_id,
            access_mode=access_mode, env=env)