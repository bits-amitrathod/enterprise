odoo.define('web_studio.HomeMenu', function (require) {
"use strict";

var core = require('web.core');
var web_client = require('web.web_client');
var HomeMenu = require('web_enterprise.HomeMenu');

var bus = require('web_studio.bus');

var QWeb = core.qweb;

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
        web_client.openAppCreator().then(function () {
            core.bus.trigger('toggle_mode', true, false);
        });
    },
});

});
