odoo.define('web_studio.ReportEditorSidebar', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var relational_fields = require('web.relational_fields');
var Widget = require('web.Widget');
var FieldManagerMixin = require('web_studio.FieldManagerMixin');

var Many2ManyTags = relational_fields.FieldMany2ManyTags;

return Widget.extend(FieldManagerMixin, {
    template: 'web_studio.ReportEditorSidebar',
    custom_events: _.extend({}, FieldManagerMixin.custom_events, {
        field_changed: 'field_changed',
    }),
    events: {
        'change input': 'change_report',
        'click .o_web_studio_xml_editor': 'on_xml_editor',
        'click .o_web_studio_parameters': 'on_parameters',
    },
    init: function(parent, report) {
        FieldManagerMixin.init.call(this);
        this._super.apply(this, arguments);
        this.debug = core.debug;
        this.report = report;
    },
    willStart: function() {
        var self = this;
        return this._super.apply(this, arguments).then(function() {
            if (self.report.groups_id.length === 0) { return; }

            // many2many field expects to receive: a list of {id, name, display_name}
            var def = new Model('res.groups')
                .query(['id', 'name', 'display_name'])
                .filter([['id', 'in', self.report.groups_id]])
                .all();

            return def.then(function(result) {
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
            record_id = self.datamodel.make_record('ir.model.fields', [{
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
            record_id = self.datamodel.make_record('ir.model.fields', [{
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
