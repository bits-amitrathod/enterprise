odoo.define('web_studio.HomeMenu', function (require) {
"use strict";

var core = require('web.core');
var session = require('web.session');
var WebClient = require('web.WebClient');
var web_client = require('web.web_client');
var HomeMenu = require('web_enterprise.HomeMenu');

var bus = require('web_studio.bus');

var QWeb = core.qweb;

/*
 * Notice:
 *  some features (like seeing the home menu background) are available
 *  even the user is not a system user, this is why there are two different
 *  includes in this file.
 */

HomeMenu.include({
    /**
     * @override
     */
    start: function () {
        this._setBackgroundImage();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {Object} menuData
     * @param {boolean} [menuData.background_image]
     */
    _processMenuData: function (menuData) {
        this._hasCustomBackground = menuData.background_image;
        return this._super.apply(this, arguments);
    },
    /**
     * Put the home menu background as the cover of current `$el`.
     *
     * @private
     */
    _setBackgroundImage: function () {
        if (this._hasCustomBackground) {
            var url = session.url('/web/image', {
                model: 'res.company',
                id: session.company_id,
                field: 'background_image',
            });
            this.$el.css({
                "background-image": "url(" + url + ")",
                "background-size": "cover",
            });
        }
    },
});

WebClient.include({
    /**
     * Adds a class on the webclient on top of the o_home_menu_background
     * class to inform that the home menu is customized.
     *
     * @override
     */
    toggle_home_menu: function (display) {
        this._super.apply(this, arguments);
        this.$el.toggleClass('o_home_menu_background_custom', display && !!this.menu_data.background_image);
    },
});

if (!session.is_system) {
    return;
}

HomeMenu.include({
    events: _.extend(HomeMenu.prototype.events, {
        'click .o_web_studio_new_app': '_onNewApp',
    }),
    /**
     * @override
     */
    start: function () {
        bus.on('studio_toggled', this, this.toggleStudioMode);
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    on_attach_callback: function () {
        this.in_DOM = true;
        if (this._inStudioMode) {
            this._renderNewApp();
        } else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * @override
     */
    on_detach_callback: function () {
        this._super.apply(this, arguments);
        this.in_DOM = false;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {boolean} [display]
     */
    toggleStudioMode: function (display) {
        this._inStudioMode = display;
        if (!this.in_DOM) {
            return;
        }
        if (display) {
            this.on_detach_callback();  // de-bind hanlders on home menu
            this.in_DOM = true;  // avoid effect of on_detach_callback
            this._renderNewApp();
        } else {
            this._$newApp.remove();
            this.on_attach_callback();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add the 'New App' icon.
     *
     * @private
     */
    _renderNewApp: function () {
        this._state = this._getInitialState();
        this._render();
        this._$newApp = $(QWeb.render('web_studio.AppCreator.NewApp'));
        this._$newApp.appendTo(this.$('.o_apps'));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onNewApp: function (ev) {
        ev.preventDefault();
        web_client.openStudio('app_creator').then(function () {
            core.bus.trigger('toggle_mode', true, false);
        });
    },
});

});
