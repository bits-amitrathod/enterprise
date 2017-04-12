odoo.define('web_enterprise.UserMenu', function (require) {
"use strict";

/**
 * This file includes the UserMenu widget defined in Community to add or
 * override actions only available in Enterprise.
 */

var core = require('web.core');
var Dialog = require('web.Dialog');
var UserMenu = require('web.UserMenu');

var _t = core._t;
var QWeb = core.qweb;

UserMenu.include({

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _onMenuSupport: function () {
        window.open('https://www.odoo.com/help', '_blank');
    },
    /**
     * @private
     */
    _onMenuShortcuts: function() {
        new Dialog(this, {
            size: 'large',
            dialogClass: 'o_act_window',
            title: _t("Keyboard Shortcuts"),
            $content: $(QWeb.render("UserMenu.shortcuts"))
        }).open();
    },
});

});
