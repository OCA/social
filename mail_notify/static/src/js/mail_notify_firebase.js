odoo.define('mail_notify.Firebase', function (require) {
    "use strict";
    var rpc = require('web.rpc');
    var config = rpc.query({
        model: 'ir.config_parameter',
        method: 'get_fcm_config',
    }).then(function(result){
        if (result.is_fcm_enabled) {
            var firebaseConfig = {
                messagingSenderId: result.fcm_messaging_id
            };
            firebase.initializeApp(firebaseConfig);
            var messaging = firebase.messaging();
            messaging.usePublicVapidKey(result.fcm_vapid_key);
            messaging.getToken().then((currentToken) => {
                if (currentToken) {
                    sendTokenToServer(currentToken);
                }
            }).catch((err) => {
                console.log('An error occurred while retrieving token. ', err);
            });
            messaging.onTokenRefresh(() => {
                messaging.getToken().then((refreshedToken) => {
                    setTokenSentToServer(false);
                    sendTokenToServer(refreshedToken);
                }).catch((err) => {
                    console.log('Unable to retrieve refreshed token ', err);
                });
            });
            function sendTokenToServer(currentToken) {
                if (!isTokenSentToServer()) {
                    rpc.query({
                        model:  'res.users.token',
                        method: 'add_token',
                        args: [currentToken]
                    });
                    setTokenSentToServer(true);
                }
            }
            function isTokenSentToServer() {
                return window.localStorage.getItem('sentToServer') === '1';
            }
            function setTokenSentToServer(sent) {
                window.localStorage.setItem('sentToServer', sent ? '1' : '0');
            }
        }
    });
});
