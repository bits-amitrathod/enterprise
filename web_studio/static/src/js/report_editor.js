odoo.define('web_studio.ReportEditor', function (require) {
"use strict";

var ReportAction = require('report.client_action');
var core = require('web.core');
var customize = require('web_studio.customize');
var ReportEditorSidebar = require('web_studio.ReportEditorSidebar');
var XMLEditor = require('web_studio.XMLEditor');

var ReportEditor = ReportAction.extend({

    template: 'web_studio.report_editor',
    custom_events: {
        'studio_edit_report': 'edit_report',
        'open_report_form': 'open_report_form',
        'open_xml_editor': 'open_xml_editor',
        'close_xml_editor': 'close_xml_editor',
        'save_xml_editor': 'save_xml_editor',
    },

    init: function(parent, action, options) {
        options = options || {};
        options = _.extend(options, {
            report_url: '/report/html/' + action.report_name + '/' + action.active_ids,
            report_name: action.report_name,
            report_file: action.report_file,
            name: action.name,
            display_name: action.display_name,
            context: {
                active_ids: action.active_ids.split(','),
            },
        });
        this.view_id = action.view_id;
        this.res_model = 'ir.actions.report.xml';
        this.res_id = action.id;
        this._super.apply(this, arguments);
    },
    willStart: function() {
        var self = this;

        return this._super.apply(this, arguments).then(function() {
            return self.rpc('ir.actions.report.xml', 'read')
                .args([[self.res_id]])
                .exec()
                .then(function (report) {
                    self.sidebar = new ReportEditorSidebar(self, report[0]);
                });
        });
    },
    start: function() {
        var self = this;

        return this._super.apply(this, arguments).then(function() {
            return self.sidebar.prependTo(self.$el);
        });
    },
    _update_control_panel_buttons: function () {
        this._super.apply(this, arguments);
        // the edit button is available in Studio even if not in debug mode
        this.$buttons.filter('div.o_edit_mode_available').toggle(this.edit_mode_available && ! this.in_edit_mode);
    },
    edit_report: function (event) {
        var args = event.data.args;
        if (!args) { return; }

        customize.edit_report(event.data.report, args);
    },
    open_report_form: function() {
        var options = {
            keep_state: true,
        };
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: this.res_model,
            res_id: this.res_id,
            views: [[false, 'form']],
            target: 'current',
        }, options);
    },
    open_xml_editor: function () {
        var self = this;

        this.XMLEditor = new XMLEditor(this, this.view_id, {
            position: 'left',
            doNotLoadLess: true,
        });

        $.when(this.XMLEditor.prependTo(this.$el)).then(function() {
            self.sidebar.$el.detach();
        });
    },
    close_xml_editor: function () {
        this.XMLEditor.destroy();
        this.sidebar.$el.prependTo(this.$el);
    },
    save_xml_editor: function (event) {
        var self = this;

        return customize.edit_view_arch(
            event.data.view_id,
            event.data.new_arch
        ).then(function() {
            // reload iframe
            self.$('iframe').attr('src', self.report_url);

            if (event.data.on_success) {
                event.data.on_success();
            }
        });
    },
});

core.action_registry.add('studio_report_editor', ReportEditor);

});
