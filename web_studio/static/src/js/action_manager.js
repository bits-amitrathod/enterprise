odoo.define('web_studio.ActionManager', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');


// Includes the ActionManger to handle restoring of an action stack
ActionManager.include({
    restore_action_stack: function (action_stack) {
        var self = this;
        var def;
        var to_destroy = this.action_stack;
        var last_action = _.last(action_stack);
        this.action_stack = action_stack;

        if (last_action && last_action.action_descr.id) {
            var view_type = last_action.get_active_view && last_action.get_active_view();
            var res_id = parseInt($.deparam(window.location.hash.slice(1)).id);

            // The action could have been modified (name, view_ids, etc.)
            // so we need to use do_action to reload it.
            def = this.do_action(last_action.action_descr.id, {
                view_type: view_type,
                replace_last_action: true,
                res_id: res_id,
                additional_context: last_action.action_descr.context,
            });
        } else {
            def = $.Deferred().reject();
        }
        return def.fail(function () {
            self.clear_action_stack();
            self.trigger_up('show_app_switcher');
        }).always(this.clear_action_stack.bind(this, to_destroy));
    },

    clear_action_stack: function (action_stack) {
        action_stack = action_stack && _.reject(action_stack, {keep_alive: true});
        this._super(action_stack);
    },

    do_push_state: function () {
        if (this.inner_action) {
            var inner_action_descr = this.inner_action.get_action_descr();
            if (inner_action_descr.keep_state) {
                return;
            }
        }
        this._super.apply(this, arguments);
    },

    do_action: function(action, options) {
        if (_.isObject(action) && 'keep_state' in options) {
            action.keep_state = options.keep_state;
        }
        return this._super.apply(this, arguments);
    },
});

});
