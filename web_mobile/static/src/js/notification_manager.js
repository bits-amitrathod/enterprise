odoo.define('web_mobile.notification_manager', function (require) {
"use strict";

var NotificationManager = require('web.NotificationManager');

var mobile = require('web_mobile.rpc');

NotificationManager.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    display: function () {
        if (mobile.methods.vibrate) {
            mobile.methods.vibrate({'duration': 100});
        }
        return this._super.apply(this, arguments);
    },
});

});
