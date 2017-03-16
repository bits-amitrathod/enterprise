odoo.define('web_studio.Main', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var dom = require('web.dom');
var form_common = require('web.view_dialogs');
var Widget = require('web.Widget');

var bus = require('web_studio.bus');
var customize = require('web_studio.customize');
var ActionEditor = require('web_studio.ActionEditor');
var ViewEditorManager = require('web_studio.ViewEditorManager');

var _t = core._t;
var _lt = core._lt;

var Main = Widget.extend({
    className: 'o_web_studio_client_action',
    error_messages: {
        'wrong_xpath': _lt("This operation caused an error, probably because a xpath was broken"),
        'view_rendering': _lt("The requested change caused an error in the view. It could be because a field was deleted, but still used somewhere else."),
    },
    custom_events: {
        'studio_default_view': '_onSetDefaultView',
        'studio_disable_view': '_onDisableView',
        'studio_edit_view': '_onEditView',
        'studio_new_view': '_onNewView',
        'studio_set_another_view': '_onSetAnotherView',
        'studio_edit_action': '_onEditAction',
        'studio_error': '_onShowError',
    },
    /**
     * @constructor
     * @param {Object} options
     * @param {Object} options.action - action description
     * @param {String} options.active_view
     * @param {Object} options.view_env - view environment
     * @param {Boolean} options.chatter_allowed
     */
    init: function (parent, context, options) {
        this._super.apply(this, arguments);
        this.action = options.action;
        this.active_view = options.active_view;
        this.view_env = options.view_env;
        this.chatter_allowed = options.chatter_allowed;
    },
    /**
     * @override
     */
    willStart: function () {
        if (!this.action) {
            return $.Deferred().reject();
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    start: function () {
        this.set('title', _t('Studio'));
        if (this.active_view) {
            // directly edit the active view instead of the action
            return this._onEditView({data: {view_type: this.active_view}});
        } else {
            var view_types = this.action.view_mode.split(',');
            this.action_editor = new ActionEditor(this, this.action, view_types);
            return $.when(
                this.action_editor.appendTo(this.$el),
                this._super.apply(this, arguments)
            );
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {String} view_mode
     * @param {Integer} view_id
     * @returns {Deferred}
     */
    _setAnotherView: function (view_mode, view_id) {
        var self = this;
        var def = customize.setAnotherView(this.action.id, view_mode, view_id);
        return def.then(function (result) {
            self.do_action('action_web_studio_main', {
                action: result,
                disable_edition: true,
            });
        });
    },
    /**
     * @private
     * @param {String} view_mode
     * @returns {Deferred}
     */
    _writeViewMode: function (view_mode, initial_view_mode) {
        var self = this;
        var def = customize.editAction(this.action, {view_mode: view_mode});
        return def.then(function (result) {
            if (initial_view_mode) {
                result.initial_view_types = initial_view_mode.split(',');
            }
            self.do_action('action_web_studio_main', {
                action: result,
                disable_edition: true,
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     */
    _onDisableView: function (event) {
        var view_type = event.data.view_type;
        var view_mode = _.without(this.action.view_mode.split(','), view_type);

        this._writeViewMode(view_mode.toString());
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onEditAction: function (event) {
        var self = this;

        var args = event.data.args;
        if (!args) { return; }

        customize.editAction(this.action, args).then(function (result) {
            self.action = result;
        });
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onEditView: function (event) {
        var self = this;
         // TODO: add studio mode in session context instead?
        var context = _.extend({}, this.action.context, { studio: true});
        var options = {};
        var views = this.action.views.slice();
        var view_type = event.data.view_type;

        // search is not in action.view
        options.load_filters = true;
        var searchview_id = this.action.search_view_id && this.action.search_view_id[0];
        views.push([searchview_id || false, 'search']);

        var view = _.find(views, function (el) { return el[1] === view_type; });
        var view_id = view && view[0];

        // TODO: only to generate a context ; should be removed
        // we should probably use a _rpc and not loadViews
        var dataset = new data.DataSet(this, this.action.res_model, context);

        // the default view needs to be created before `loadViews` or the
        // renderer will not be aware that a new view exists
        var arch_def = customize.getStudioViewArch(this.action.res_model, view_type, view_id);
        return arch_def.then(function (studio_view) {
            // TODO: this probably needs to change ; not sure fields_view still needed in view_editor_manager
            var view_def = self.loadViews(self.action.res_model, dataset.get_context(), views, options);
            return view_def.then(function (fields_views) {
                var params = {
                    fields_view: fields_views[view_type],
                    view_env: self.view_env,
                    chatter_allowed: self.chatter_allowed,
                    studio_view_id: studio_view.studio_view_id,
                    studio_view_arch: studio_view.studio_view_arch,
                };
                self.view_editor = new ViewEditorManager(self, params);

                var fragment = document.createDocumentFragment();
                return self.view_editor.appendTo(fragment).then(function () {
                    if (self.action_editor) {
                        dom.detach([{widget: self.action_editor}]);
                    }
                    dom.append(self.$el, [fragment], {
                        in_DOM: true,
                        callbacks: [{widget: self.view_editor}],
                    });

                    bus.trigger('edition_mode_entered', view_type);
                });
            });
        });
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onNewView: function (event) {
        var self = this;
        var view_type = event.data.view_type;
        var view_mode = this.action.view_mode + ',' + view_type;
        var def = customize.addViewType(this.action, view_type, {
            view_mode: view_mode,
        });
        def.then(function (result) {
            self.do_action('action_web_studio_main', {
                action: result,
                active_view: view_type,
                disable_edition: true,
            });
        });
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onSetAnotherView: function (event) {
        var self = this;
        var view_type = event.data.view_type;

        new form_common.SelectCreateDialog(this, {
            res_model: 'ir.ui.view',
            title: _t('Select a view'),
            disable_multiple_selection: true,
            no_create: true,
            domain: [
                ['type', '=', view_type],
                ['mode', '=', 'primary'],
                ['model', '=', this.action.res_model],
            ],
            on_selected: function (view_id) {
                self._setAnotherView(view_type, view_id[0]);
            }
        }).open();
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onSetDefaultView: function (event) {
        var view_type = event.data.view_type;
        var view_mode = _.without(this.action.view_mode.split(','), view_type);
        view_mode.unshift(view_type);
        view_mode = view_mode.toString();

        this._writeViewMode(view_mode, this.action.view_mode);
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onShowError: function (event) {
        this.do_warn(_t("Error"), this.error_messages[event.data.error]);
    },
});

core.action_registry.add('action_web_studio_main', Main);

});
