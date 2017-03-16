odoo.define('web_studio.ReportEditorSidebar', function (require) {
"use strict";

var core = require('web.core');
var relational_fields = require('web.relational_fields');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var Widget = require('web.Widget');

var Many2ManyTags = relational_fields.FieldMany2ManyTags;
var Many2One = relational_fields.FieldMany2One;

return Widget.extend(StandaloneFieldManagerMixin, {
    template: 'web_studio.ReportEditorSidebar',
    events: {
        'change input': '_onChangeReport',
        'click .o_web_studio_xml_editor': '_onXMLEditor',
        'click .o_web_studio_parameters': '_onParameters',
    },
    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} report
     */
    init: function(parent, report) {
        this._super.apply(this, arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.debug = core.debug;
        this.report = report;
    },
    /**
     * @override
     */
    willStart: function() {
        var self = this;
        return this._super.apply(this, arguments).then(function() {
            if (self.report.groups_id.length === 0) {
                return $.Deferred().resolve();
            }

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
    /**
     * @override
     */
    start: function() {
        var self = this;
        return this._super.apply(this, arguments).then(function() {
            // add many2many for groups_id
            var groups = self.report.groups_id;
            var recordID1 = self.model.makeRecord('ir.model.fields', [{
                name: 'groups_id',
                relation: 'res.groups',
                relational_value: self.groups_info,
                type: 'many2many',
                value: groups,
            }]);
            var options1 = {
                mode: 'edit',
                no_quick_create: true,  // FIXME: enable add option
            };
            var record1 = self.model.get(recordID1);
            self.many2many = new Many2ManyTags(self, 'groups_id', record1, options1);
            this._registerWidget(recordID1, 'model', this.many2many);
            self.many2many.appendTo(self.$('.o_groups'));

            // add many2one for paperformat_id
            var recordID2 = self.model.makeRecord('ir.model.fields', [{
                name: 'paperformat_id',
                relation: 'report.paperformat',
                type: 'many2many',
            }]);
            var options2 = {
                mode: 'edit',
                no_quick_create: true,  // FIXME: enable add option
            };
            var record2 = self.model.get(recordID2);
            self.many2one = new Many2One(self, 'paperformat_id', record2, options2);
            this._registerWidget(recordID2, 'model', this.many2one);
            self.many2one.appendTo(self.$el.find('.o_paperformat_id'));
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeReport: function(ev) {
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
    /**
     * @private
     * @override
     * @param {OdooEvent} ev
     */
    _onFieldChanged: function (ev) {
        StandaloneFieldManagerMixin._onFieldChanged.apply(this, arguments);

        var args = {};
        var field_name = ev.data.name;
        if (field_name === 'groups_id') {
            args[field_name] = this.many2many.value;
        } else if (field_name === 'paperformat_id') {
            args[field_name] = this.many2one.value.res_id;
        }
        this.trigger_up('studio_edit_report', {report: this.report, args: args});
    },
    /**
     * @private
     */
    _onParameters: function () {
        this.trigger_up('open_report_form');
    },
    /**
     * @private
     */
    _onXMLEditor: function () {
        this.trigger_up('open_xml_editor');
    },
});

});
