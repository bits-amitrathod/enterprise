odoo.define('web_studio.ReportEditorSidebar', function (require) {
"use strict";

var core = require('web.core');
var relational_fields = require('web.relational_fields');
var Widget = require('web.Widget');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');


return Widget.extend(StandaloneFieldManagerMixin, {
    template: 'web_studio.ReportEditorSidebar',
    custom_events: _.extend({}, StandaloneFieldManagerMixin.custom_events, {
        field_changed: 'field_changed',
    }),
    events: {
        'change input': 'change_report',
        'click .o_web_studio_xml_editor': 'on_xml_editor',
        'click .o_web_studio_parameters': 'on_parameters',
    },
    init: function(parent, report) {
        this._super.apply(this, arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.debug = core.debug;
        this.report = report;
    },
    willStart: function() {
        var self = this;
        return this._super.apply(this, arguments).then(function() {
            if (self.report.groups_id.length === 0) { return; }

            // many2many field expects to receive: a list of {id, name, display_name}
            return self._rpc({
                    model: 'res.groups',
                    method: 'search_read',
                    args: [[['id', 'in', self.report.groups_id]], ['id', 'name', 'display_name']],
                })
                .then(function(result) {
                    self.groups_info = result;
                });
        });
    },
    start: function() {
        var self = this;
        return this._super.apply(this, arguments).then(function() {

            var record_id;
            var options;
            // Add many2many for groups_id
            var groups = self.report.groups_id;
            record_id = self.model.makeRecord('ir.model.fields', [{
                name: 'groups_id',
                relation: 'res.groups',
                relational_value: self.groups_info,
                type: 'many2many',
                value: groups,
            }]);
            options = {
                mode: 'edit',
                no_quick_create: true,  // FIXME: enable add option
            };
            var Many2ManyTags = relational_fields.FieldMany2ManyTags;
            self.many2many = new Many2ManyTags(self, 'groups_id', self.datamodel.get(record_id), options);
            self.many2many.appendTo(self.$('.o_groups'));
            // add many2one for paperformat_id
            record_id = self.model.makeRecord('ir.model.fields', [{
                name: 'paperformat_id',
                relation: 'report.paperformat',
                type: 'many2many',
            }]);
            options = {
                mode: 'edit',
                no_quick_create: true,  // FIXME: enable add option
            };
            var Many2one = relational_fields.FieldMany2One;
            self.many2one = new Many2one(self, 'paperformat_id', self.datamodel.get(record_id), options);
            self.many2one.appendTo(self.$el.find('.o_paperformat_id'));
        });
    },
    change_report: function(ev) {
        var $input = $(ev.currentTarget);
        var attribute = $input.attr('name');
        if (attribute) {
            var new_attrs = {};
            if ($input.attr('type') === 'checkbox') {
                new_attrs[attribute] = $input.is(':checked') ? 'True': '';
            } else {
                new_attrs[attribute] = $input.val();
            }
            this.trigger_up('studio_edit_report', {report: this.report, args: new_attrs});
        }
    },
    on_parameters: function() {
        this.trigger_up('open_report_form');
    },
    field_changed: function(ev) {
        var args = {};
        var field_name = ev.data.name;
        if (field_name === 'groups_id') {
            args[field_name] = this.many2many.value;
        } else if (field_name === 'paperformat_id') {
            args[field_name] = this.many2one.value;
        }
        this.trigger_up('studio_edit_report', {report: this.report, args: args});
    },
    on_xml_editor: function () {
        this.trigger_up('open_xml_editor');
    },
});

});
