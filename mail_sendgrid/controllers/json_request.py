# -*- coding: utf-8 -*-
# Copyright 2016-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import json
import logging
from odoo.http import JsonRequest, Root, Response

# Monkeypatch type of request rooter to use RESTJsonRequest
old_get_request = Root.get_request
_logger = logging.getLogger(__name__)


def get_request(self, httprequest):
    if (httprequest.mimetype == "application/json" and
            httprequest.environ['PATH_INFO'].startswith('/mail')):
        return RESTJsonRequest(httprequest)
    return old_get_request(self, httprequest)


Root.get_request = get_request


class RESTJsonRequest(JsonRequest):
    """ Special RestJson Handler to enable receiving lists in JSON
        body
    """
    def __init__(self, *args):
        try:
            super(RESTJsonRequest, self).__init__(*args)
        except AttributeError:
            # The JSON may contain a list
            self.params = dict()
            self.context = dict(self.session.context)

    def _json_response(self, result=None, error=None):
        response = {}
        if error is not None:
            response['error'] = error
        if result is not None:
            response['result'] = result

        mime = 'application/json'
        body = json.dumps(response)

        return Response(
            body, headers=[('Content-Type', mime),
                           ('Content-Length', len(body))])
