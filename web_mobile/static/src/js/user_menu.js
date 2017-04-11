odoo.define('web_mobile.user_menu', function (require) {
"use strict";

var UserMenu = require('web.UserMenu');

var mobile = require('web_mobile.rpc');

// Hide the logout link in mobile
UserMenu.include({
    /**
     * @override
     */
    start: function () {
        if (mobile.methods.switchAccount) {
            this.$('a[data-menu="logout"]').addClass('hidden');
            this.$('a[data-menu="account"]').addClass('hidden');
            this.$('a[data-menu="switch"]').removeClass('hidden');
        }
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onMenuSwitch: function () {
        mobile.methods.switchAccount();
    },
});

});
