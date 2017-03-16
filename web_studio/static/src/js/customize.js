odoo.define('web_studio.customize', function(require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var data_manager = require('web.data_manager');
var Dialog = require('web.Dialog');
var studio_bus = require('web_studio.bus');
var session = require('web.session');
var NewViewDialog = require('web_studio.NewViewDialog');
var _t = core._t;

// this file should regroup all methods required to do a customization,
// so, basically all write/update/delete operations made in web_studio.

return {
    create_new_app: function(app_name, menu_name, model_id, icon) {
        var self = this;
        data_manager.invalidate();
        return ajax.jsonRpc('/web_studio/create_new_menu', 'call', {
            app_name: app_name,
            menu_name: menu_name,
            model_id: model_id,
            is_app: true,
            icon: icon,
            context: session.user_context,
        }).fail(function(result, error) {
            Dialog.alert(self, _t('This model already exists. Please specify another model.'));
        });
    },

    create_new_menu: function(menu_name, parent_id, model_id) {
        data_manager.invalidate();
        return ajax.jsonRpc('/web_studio/create_new_menu', 'call', {
            menu_name: menu_name,
            model_id: model_id,
            parent_id: parent_id,
            context: session.user_context,
        });
    },

    create_new_report: function(model_name, template_name) {
        return ajax.jsonRpc('/web_studio/create_new_report', 'call', {
            model_name: model_name,
            template_name: template_name,
            context: session.user_context,
        });
    },

    set_background_image: function(attachment_id) {
        return ajax.jsonRpc('/web_studio/set_background_image', 'call', {
            attachment_id: attachment_id,
            context: session.user_context,
        });
    },

    add_view_type: function(action, view_type, args) {
        var self = this;
        var def = $.Deferred();
        data_manager.invalidate();
        ajax.jsonRpc('/web_studio/add_view_type', 'call', {
            action_type: action.type,
            action_id: action.id,
            res_model: action.res_model,
            view_type: view_type,
            args: args,
            context: session.user_context,
        }).then(function(result) {
            if (result !== true) {
                var options = {
                    action: action,
                    callback: function(){
                        self.edit_action(action, args).then(function(result) {
                            def.resolve(result);
                        });
                    },
                };
                // TODO find better way to check which view_type is being access
                if (result.indexOf('gantt') !== -1) {
                    options.view_type = 'gantt';
                    new NewViewDialog(this, options).open();
                } else if (result.indexOf('Calendar') !== -1) {
                    options.view_type = 'calendar';
                    new NewViewDialog(this, options).open();
                } else {
                    Dialog.alert(this, result);
                    def.reject();
                }
            } else {
                self._reload_action(action.id)
                    .then(def.resolve.bind(def))
                    .fail(def.reject.bind(def));
            }
        });
        return def;
    },

    edit_action: function(action, args) {
        var self = this;
        var def = $.Deferred();
        data_manager.invalidate();
        ajax.jsonRpc('/web_studio/edit_action', 'call', {
            action_type: action.type,
            action_id: action.id,
            args: args,
            context: session.user_context,
        }).then(function(result) {
            if (result !== true) {
                Dialog.alert(self, result);
                def.reject();
            } else {
                self._reload_action(action.id)
                    .then(def.resolve.bind(def))
                    .fail(def.reject.bind(def));
            }
        }).fail(def.reject.bind(def));
        return def;
    },

    edit_report: function(report, values) {
        return ajax.jsonRpc('/web_studio/edit_report', 'call', {
            report_id: report.id,
            values: values,
            context: session.user_context,
        });
    },

    set_another_view: function(action_id, view_mode, view_id) {
        var self = this;
        data_manager.invalidate();
        return ajax.jsonRpc('/web_studio/set_another_view', 'call', {
            action_id: action_id,
            view_mode: view_mode,
            view_id: view_id,
            context: session.user_context,
        }).then(function() {
            return self._reload_action(action_id);
        });
    },

    // The point of this function is to receive a list of customize operations
    // to do. This is the "operations" variable.
    edit_view: function(view_id, studio_view_arch, operations) {
        data_manager.invalidate();
        return ajax.jsonRpc('/web_studio/edit_view', 'call', {
            view_id: view_id,
            studio_view_arch: studio_view_arch,
            operations: operations,
            context: session.user_context,
        });
    },

    // This is used when the view is edited with the XML editor: the whole arch
    // is replaced by a new one.
    edit_view_arch: function(view_id, view_arch) {
        data_manager.invalidate();
        return ajax.jsonRpc('/web_studio/edit_view_arch', 'call', {
            view_id: view_id,
            view_arch: view_arch,
            context: session.user_context,
        });
    },

    get_email_alias: function(model_name) {
        return ajax.jsonRpc('/web_studio/get_email_alias', 'call', {
            model_name: model_name,
        }).then(function(result) {
            return result;
        });
    },

    set_email_alias: function(model_name, value) {
        return ajax.jsonRpc('/web_studio/set_email_alias', 'call', {
            model_name: model_name,
            value: value,
        });
    },

    get_default_value: function(model_name, field_name) {
        return ajax.jsonRpc('/web_studio/get_default_value', 'call', {
            model_name: model_name,
            field_name: field_name,
        }).then(function(result) {
            return {
                default_value: result,
            };
        });
    },

    set_default_value: function(model_name, field_name, value) {
        return ajax.jsonRpc('/web_studio/set_default_value', 'call', {
            model_name: model_name,
            field_name: field_name,
            value: value,
        });
    },

    get_studio_view_arch: function(model, view_type, view_id) {
        data_manager.invalidate();
        return ajax.jsonRpc('/web_studio/get_studio_view_arch', 'call', {
            model: model,
            view_type: view_type,
            view_id: view_id,
            context: session.user_context,
        });
    },

    _reload_action: function(action_id) {
        return data_manager.load_action(action_id).then(function(new_action) {
            studio_bus.trigger('action_changed', new_action);
            return new_action;
        });
    },
};

});
