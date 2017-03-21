odoo.define('web_gantt.GanttView', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var core = require('web.core');
var GanttModel = require('web_gantt.GanttModel');
var GanttRenderer = require('web_gantt.GanttRenderer');
var GanttController = require('web_gantt.GanttController');
var view_registry = require('web.view_registry');

var _t = core._t;
var _lt = core._lt;

// gather the fields to get
var fields_to_gather = [
    "date_start",
    "date_delay",
    "date_stop",
    "consolidation",
    "progress",
];

var scales = [
    'day',
    'week',
    'month',
    'year'
];

var GanttView = AbstractView.extend({
    display_name: _lt('Gantt'),
    icon: 'fa-tasks',
    config: {
        Model: GanttModel,
        Controller: GanttController,
        Renderer: GanttRenderer,
        js_libs: ["/web_gantt/static/lib/dhtmlxGantt/sources/dhtmlxcommon.js"],
        css_libs: ["/web_gantt/static/lib/dhtmlxGantt/codebase/dhtmlxgantt.css"],
    },
    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        var arch = viewInfo.arch;
        var fields = viewInfo.fields;
        var mapping = {name: 'name'};

        // gather the fields to get
        _.each(fields_to_gather, function(field) {
            if (arch.attrs[field]) {
                mapping[field] = arch.attrs[field];
            }
        });

        // consolidation exclude, get the related fields
        if (arch.attrs.consolidation_exclude) {
            _.each(arch.attrs.consolidation_exclude, function(field_name) {
                mapping.consolidation_exclude = field_name;
            });
        }
        var scale = arch.attrs.scale_zoom;
        if (!_.contains(scales, scale)) {
            scale = "month";
        }

        // TODO : make sure th 'default_group_by' attribute works
        // var default_group_by = [];
        // if (arch.attrs.default_group_by) {
        //     default_group_by = arch.attrs.default_group_by.split(',');
        // }

        this.controllerParams.context = params.context || {};
        this.controllerParams.title = params.action ? params.action.name : _t("Gantt");
        this.loadParams.fields = fields;
        this.loadParams.mapping = mapping;
        this.loadParams.scale = scale;
        this.loadParams.initialDate = moment(params.initialDate || new Date());
    },
});

view_registry.add('gantt', GanttView);

return GanttView;

});
