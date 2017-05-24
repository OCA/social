# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __openerp__.py
#
##############################################################################
import logging
import simplejson

from openerp.http import JsonRequest, Root, Response

_logger = logging.getLogger(__name__)

# Monkeypatch type of request rooter to use RESTJsonRequest
old_get_request = Root.get_request


def get_request(self, httprequest):
    if (httprequest.mimetype == "application/json" and
            httprequest.environ['PATH_INFO'].startswith('/sendgrid')):
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
        body = simplejson.dumps(response)

        return Response(
            body, headers=[('Content-Type', mime),
                           ('Content-Length', len(body))])
