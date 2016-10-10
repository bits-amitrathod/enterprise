odoo.define('web_grid.MockServer', function (require) {
"use strict";

var MockServer = require('web.MockServer');

MockServer.include({
    _performRpc: function(route, args) {
        if (args.method === 'read_grid') {
            return this._mockReadGrid(args.model, args.kwargs);
        } else {
            return this._super(route, args);
        }
    },
    _mockReadGrid: function(model, kwargs) {
        var self = this;

        // various useful dates
        var gridAnchor = moment(kwargs.context.grid_anchor || this.currentDate);
        var today = moment();
        var span = kwargs.range.span;
        var start = gridAnchor.clone().startOf(span === 'week' ? 'isoWeek' : 'month');
        var end = gridAnchor.clone().endOf(span === 'week' ? 'isoWeek' : 'month');
        var nextAnchor = gridAnchor.clone().add(1, span === 'week' ? 'weeks' : 'month').format('YYYY-MM-DD');
        var prevAnchor = gridAnchor.clone().subtract(1, span === 'week' ? 'weeks' : 'month').format('YYYY-MM-DD');

        // compute columns
        var columns = [];
        var current = start.clone().subtract(1, 'days');

        while (!current.isSame(end, 'days')) {
            current.add(1, 'days');
            var dayStr = current.format('YYYY-MM-DD');
            var nextDayStr = current.clone().add(1, 'days').format('YYYY-MM-DD');
            columns.push({
                is_current: current.isSame(today),
                domain: ["&", ["date", ">=", dayStr], ["date", "<", nextDayStr]],
                values: {date: [dayStr + '/' + nextDayStr, current.format('ddd,\nMMM\u00a0DD')]}
            });
        }

        // compute rows and grid
        var rows = [];
        var grid = [];
        for (var i = 0; i < this.data[model].records.length; i++) {
            var record = this.data[model].records[i];
            var recordDate = record[kwargs.col_field];
            if (moment(recordDate).isBetween(start, end, null, '[]')) {
                // generate row
                var values = {};
                _.each(kwargs.row_fields, function(fieldName) {
                    var field = self.data[model].fields[fieldName];
                    if (field.type === 'many2one') {
                        var relatedRecord = _.findWhere(self.data[field.relation].records, {id: record[fieldName]});
                        values[fieldName] = [relatedRecord.id, relatedRecord.display_name];
                    } else {
                        values[fieldName] = record[fieldName];
                    }
                });
                rows.push({
                    domain: [],
                    values: values,
                });

                // generate cells
                var current = start.clone();
                var cells = [];
                for (var j = 0; j < 7; j++) {
                    var isCurrent = moment(recordDate).isSame(current);
                    cells.push({
                        size: isCurrent ? 1 : 0,
                        value: isCurrent ? record[kwargs.cell_field] : 0,
                        is_current: moment(recordDate).isSame(today),
                        domain: [],
                    });
                    current.add(1, "days");
                }
                grid.push(cells);

            }
        }

        return {
            cols: columns,
            rows: rows,
            grid: grid,
            prev: {
                default_date: prevAnchor,
                grid_anchor: prevAnchor,
            },
            next: {
                default_date: nextAnchor,
                grid_anchor: nextAnchor,
            },
        };
    },
});

});