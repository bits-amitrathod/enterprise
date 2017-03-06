odoo.define('web_gantt.GanttModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');

// optional behavior if this model fields is contains in the view
var fields_optional = [
    "color",
    "active",
];

return AbstractModel.extend({
    init: function () {
        this._super.apply(this, arguments);
        this.gantt = null;
    },
    get: function () {
        return _.extend({}, this.gantt);
    },
    load: function (params) {
        this.modelName = params.modelName;
        this.mapping = params.mapping;
        this.fields = params.fields;
        this.gantt = {
            fields: this.fields,
            mapping: this.mapping,
            to_grouped_by: params.groupedBy,
            domain: params.domain,
            context: params.context,
        };
        this._setFocusDate(params.initialDate, params.scale);
        return this._load_gantt();
    },
    _setFocusDate: function (focusDate, scale) {
        this.gantt.scale = scale;
        this.gantt.focus_date = focusDate;
        this.gantt.start_date = focusDate.clone().subtract(1, scale).startOf(scale);
        this.gantt.to_date = focusDate.clone().add(3, scale).endOf(scale);
        this.gantt.end_date = this.gantt.to_date.add(1, scale);
        this.gantt.date_display = this._formatDate(focusDate, scale);
    },
    setFocusDate: function (focusDate) {
        this._setFocusDate(focusDate, this.gantt.scale);
    },
    reload: function () {
        return this._load_gantt();
    },

    _load_gantt: function () {
        var self = this;
        return this._rpc(this.modelName, 'search_read')
            .withContext(this.gantt.context)
            .withDomain(this.gantt.domain.concat(this._focus_domain()))
            .exec()
            .then(function (data) {
                self.gantt.data = data.records;
            });
    },

    _focus_domain: function () {
        var domain = [[this.gantt.mapping.date_start, '<', this.gantt.to_date.locale('en').format("YYYY-MM-DD")]];
        if (this.fields[this.gantt.mapping.date_stop]) {
             domain = domain.concat([
                '|',
                [this.gantt.mapping.date_stop, ">", this.gantt.start_date.locale('en').format("YYYY-MM-DD")],
                [this.gantt.mapping.date_stop, '=', false]
            ]);
        }
        return domain;
    },

    _formatDate: function (date, scale) {
        // range date
        // Format to display it
        switch(scale) {
            case "day":
                return date.format("D MMM");
            case "week":
                var date_start = date.clone().startOf("week").format("D MMM");
                var date_end = date.clone().endOf("week").format("D MMM");
                return date_start + " - " + date_end;
            case "month":
                return date.format("MMMM YYYY");
            case "year":
                return date.format("YYYY");
        }
    },
    setScale: function (scale) {
        this._setFocusDate(this.gantt.focus_date, scale);
    },
});

});
