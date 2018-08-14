odoo.define('stock_barcode.FormWidget', function (require) {
'use strict';

var Widget = require('web.Widget');
var FormView = require('web.FormView');

var FormWidget = Widget.extend({
    'template': 'stock_barcode_form_widget',
    events: {
        'click .o_save': '_onClickSave',
        'click .o_discard': '_onClickDiscard',
    },
    custom_events: {
        'env_updated': '_onEnvUpdated',
    },

    init: function (clientAction, model, view, defaultValue, res_id, mode) {
        this._super.apply(this, arguments);
        this.model = model;
        this.view = view;
        this.res_id = res_id;
        this.defaultValue = defaultValue;
        this.mode = mode || 'edit';
    },


    willStart: function () {
        var self = this;
        return this._super().then(function () {
            return self._getFormViewController().then(function (controller) {
                self.controller = controller;
            });
        });
    },

    start: function() {
        var self = this;
        var def = this.controller.appendTo(this.$el.filter('.barcode_form_view'));
        return $.when(def, this._super()).then(function () {
            self.$el.find('.o_form_view').addClass('o_xxs_form_view');
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Create a controller for a given model, view and record.
     *
     * @private
     */
    _getFormViewController: function() {
        var self = this;
        var views = [[false, 'form']];
        var context = _.extend({}, this.defaultValue, this.context || {}, {
            form_view_ref: this.view,
        });
        return this.loadViews(this.model, context, views).then(function (fieldsViews) {
            var params = {
                context: context,
                modelName: self.model,
                userContext: self.getSession().user_context,
                mode: self.mode,
            };
            if (self.res_id) {
                params.currentId = self.res_id;
            }
            var formView = new FormView(fieldsViews.form, params);
            return formView.getController(self);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles the click on the `confirm button`.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSave: function (ev) {
        ev.stopPropagation();
        var self = this;
        var def = this.controller.saveRecord(this.controller.handle, {stayInEdit: true, reload: false});
        def.then(function () {
            var record = self.controller.model.get(self.controller.handle);
            self.trigger_up('reload', {'record': record});
        });
    },

    /**
     * Handles the click on the `discard button`.
     *
     * @private
     * @param {MouseEvent} ev
     */
     _onClickDiscard: function (ev) {
        ev.stopPropagation();
        this.trigger_up('reload');
    },

    /**
     * Stops the propagation of 'update_env' events triggered by the controllers
     * instantiated by the FormWidget.
     *
     * @override
     * @private
     */
    _onEnvUpdated: function (event) {
        event.stopPropagation();
    },
});

return FormWidget;

});
