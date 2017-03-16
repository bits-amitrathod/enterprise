odoo.define('web_studio.ActionEditorSidebar', function (require) {
"use strict";

var core = require('web.core');
var relational_fields = require('web.relational_fields');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var Widget = require('web.Widget');

var Many2ManyTags = relational_fields.FieldMany2ManyTags;

var ActionEditorSidebar = Widget.extend(StandaloneFieldManagerMixin, {
    template: 'web_studio.ActionEditorSidebar',
    events: {
        'change input, textarea': '_onActionChange',
        'click .o_web_studio_parameters': '_onParameters',
    },
    /**
     * @constructor
     * @param {Object} action
     */
    init: function (parent, action) {
        this._super.apply(this, arguments);
        StandaloneFieldManagerMixin.init.call(this);

        this.debug = core.debug;
        this.action = action;
        this.action_attrs = {
            name: action.display_name || action.name,
            help: action.help && action.help.replace(/\n\s+/g, '\n') || '',
        };
        this.groups_info = [];
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            if (self.action.groups_id.length === 0) { return; }

            // many2many field expects to receive: a list of {id, name, display_name}
            self._rpc({
                    model: 'res.groups',
                    method: 'search_read',
                    args: [[['id', 'in', self.action.groups_id]], ['id', 'name', 'display_name']],
                })
                .then(function(result) {
                    self.groups_info = result;
                });
        });
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {

            var groups = self.action.groups_id;
            // TODO: fix many2many
            var recordID = self.model.makeRecord('ir.actions.act_window', [{
                name: 'groups_id',
                relation: 'res.groups',
                relational_value: self.groups_info,
                type: 'many2many',
                value: groups,
            }]);
            var record = self.model.get(recordID);
            var options = {
                mode: 'edit',
                no_quick_create: true,  // FIXME: enable add option
            };
            self.many2many = new Many2ManyTags(self, 'groups_id', record, options);
            self._registerWidget(recordID, 'groups_id', self.many2many);
            self.many2many.appendTo(self.$el.find('.o_groups'));
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} event
     */
    _onActionChange: function (event) {
        var $input = $(event.currentTarget);
        var attribute = $input.attr('name');
        if (attribute) {
            var new_attrs = {};
            new_attrs[attribute] = $input.val();
            this.trigger_up('studio_edit_action', {args: new_attrs});
        }
    },

    /**
     * @private
     */
    _onParameters: function () {
        this.trigger_up('parameters_clicked');
    },

    /*
     * @private
     * @override
     * @param {Event} event
     */
    _onFieldChanged: function (event) {
        StandaloneFieldManagerMixin._onFieldChanged.apply(this, arguments);
        var args = {};
        args[event.data.name] = this.many2many.value;
        this.trigger_up('studio_edit_action', {args: args});
    },
});

return ActionEditorSidebar;

});
