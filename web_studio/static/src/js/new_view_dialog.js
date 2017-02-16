odoo.define('web_studio.NewViewDialog', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var data = require('web.data');
var data_manager = require('web.data_manager');
var Dialog = require('web.Dialog');
var session = require('web.session');
var _t = core._t;

var NewViewDialog = Dialog.extend({
    template: 'web_studio.NewViewDialog',
    init: function(parent, options) {
        this.GROUPABLE_TYPES = ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime'];
        this.MEASURABLE_TYPE = ['integer', 'float'];
        this.view_type = options.view_type;
        this.dataset = new data.DataSetSearch(this, options.action.res_model, options.action.domain);
        this.on_save_callback = options.callback;
        this.debug = core.debug;
        var modal_param = {
            title: _.str.sprintf(_t("Generate %s View"),this.view_type),
            size: 'medium',
            buttons: [
                {text: _t("Activate View"), classes: 'btn-primary', click: this.save},
                {text: _t("Cancel"), close: true},
            ],
        };

        this._super(parent, modal_param);
    },
    willStart: function() {
        var self = this;
        return $.when(
            data_manager.load_fields(this.dataset),
            this._super.apply(this, arguments)
        ).then(function (fields) {
            self.fields = _.sortBy(fields, function(field, key) {
                field.key = key;
                return field.string;
            });
            self.date_fields = [];
            self.row_fields = [];
            self.measure_fields = [];
            _.each(self.fields, function (field){
                if (field.store) {
                    if (field.type === 'date' || field.type === 'datetime') {
                        self.date_fields.push(field);
                    }
                    if (_.contains(self.GROUPABLE_TYPES, field.type)) {
                        self.row_fields.push(field);
                    } else if (_.contains(self.MEASURABLE_TYPE, field.type) && field.key !== 'id' && field.key !== 'sequence') {
                        self.measure_fields.push(field);
                    }
                }
            });
        });
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$modal.addClass('o_web_studio_new_view_modal');
    },
    save: function() {
        var self = this;
        var attrs = {};
        $.each(this.$('.o_web_studio_select select'), function(key, select) {
            attrs[$(select).data('field')] = $(select).val();
        });
        ajax.jsonRpc('/web_studio/create_default_view', 'call', {
            model: this.dataset.model,
            view_type: this.view_type,
            attrs: attrs,
            context: session.user_context,
        }).then(function() {
            if (self.on_save_callback) {
                self.on_save_callback();
            }
        });
        this.close();
    },

});

return NewViewDialog;

});
