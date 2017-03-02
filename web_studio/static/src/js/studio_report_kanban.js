odoo.define('web_studio.studio_report_kanban', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var KanbanView = require('web.KanbanView');
var view_registry = require('web.view_registry');

var customize = require('web_studio.customize');

var _t = core._t;

var reports = [
    {
        template_name: 'report_business',
        name: _t("Preview Business Document"),
        description: _t("(e.g. Sales order)"),
    },
    {
        template_name: 'report_blank',
        name: _t("Preview Blank Document"),
        description: _t("(empty report with footer and header)"),
    },
];

var StudioReportKanbanView = KanbanView.extend({
    custom_events: _.extend({}, KanbanView.prototype.custom_events, {
        open_record: 'open_record',
    }),

    add_record: function() {
        var model = this.dataset.context.search_default_model;
        new AddReportDialog(this, model).open();
    },

    open_record: function(event) {
        var self = this;
        this.rpc('ir.actions.report.xml', 'studio_edit')
            .args([event.data.id])
            .exec()
            .then(function(action) {
                if (action.active_ids.length) {
                    self.do_action(action);
                } else {
                    new Dialog(this, {
                        size: 'medium',
                        title: _t('No record to display.'),
                        $content: $('<div>', {
                            text: _t("First, quit Odoo Studio to create a new entity. Then, open Odoo Studio to create or edit reports."),
                        }),
                    }).open();
                }
            });
    },
});

var AddReportDialog = Dialog.extend({
    events: {
        'click .o_web_studio_report_template_item': '_create_report_from_template',
    },

    init: function(parent, model) {
        this.model = model;
        var options = {
            title: _t("Select a report template"),
            size: 'medium',
            buttons: [],
        };
        this._super(parent, options);
    },
    start: function() {
        var $message = $('<div>').addClass('o_web_studio_report_template_dialog');
        _.each(reports, function (report) {
            $message.append($('<div>').addClass('o_web_studio_report_template_item')
                .data("template_name", report.template_name)
                .append($('<div>').text(report.name))
                .append($('<span>').addClass('o_web_studio_report_template_description').text(report.description))
            );
        });
        this.$el.append($message);
        return this._super.apply(this, arguments);
    },
    _create_report_from_template: function(event) {
        var self = this;
        var template_name = $(event.currentTarget).data('template_name');
        customize.create_new_report(this.model, template_name).then(function(result) {
            self.trigger_up('open_record', {id: result.id});
            self.close();
        });
    },
});

view_registry.add('studio_report_kanban', StudioReportKanbanView);

return StudioReportKanbanView;

});
