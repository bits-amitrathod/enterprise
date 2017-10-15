odoo.define('website_crm_score.set_score', function (require) {
"use strict";

var ajax = require('web.ajax');
var rpc = require('web.rpc');
var websiteSeo = require('website.seo');
var weContext = require("web_editor.context");
var core = require('web.core');

var qweb = core.qweb;

ajax.loadXML('/website_crm_score/static/src/xml/track_page.xml', qweb);

websiteSeo.SeoConfigurator.include({
    track: null,
    start: function () {
        var def = this._super.apply(this, arguments);
        var self = this;
        this.is_tracked().then(function (data) {
            var add = $('<input type="checkbox" required="required"/>');
            if (data[0]['track']) {
                add.attr('checked','checked');
                self.track = true;
            }
            else {
                self.track = false;
            }
            self.$('h4[class="track-page"]').append(add);
        });
        return def;
    },
    is_tracked: function (val) {
        var viewid = $('html').data('viewid');
        if (!viewid) {
            return $.Deferred().reject();
        } else {
            return rpc.query({
                    model: 'ir.ui.view',
                    method: 'read',
                    args: [[viewid], ['track'], weContext.get()],
                });
        }
    },
    update: function () {
        var self = this;
        var mysuper = this._super;
        var checkbox_value = this.$('input[type="checkbox"]').is(':checked');
        if (checkbox_value !== self.track) {
            this.trackPage(checkbox_value).then(function () {
                mysuper.call(self);
            });
        }
        else {
            mysuper.call(self);
        }
    },
    trackPage: function (val) {
        var viewid = $('html').data('viewid');
        if (!viewid) {
            return $.Deferred().reject();
        } else {
            return rpc.query({
                    model: 'ir.ui.view',
                    method: 'write',
                    args: [[viewid], { track: val }, weContext.get()],
                });
        }
    },
});

});
