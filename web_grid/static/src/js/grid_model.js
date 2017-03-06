odoo.define('web_grid.GridModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');

return AbstractModel.extend({
    // inherited methods
    init: function () {
        this._super.apply(this, arguments);
        this.gridData = null;
    },
    get: function () {
        return this.gridData;
    },
    load: function (params) {
        this.modelName = params.modelName;
        this.defaultRowFields = params.rowFields;
        this.colField = params.colField;
        this.cellField = params.cellField;
        this.ranges = params.ranges;
        this.currentRange = params.currentRange;
        var rowFields = params.groupedBy.length ? params.groupedBy : this.defaultRowFields.slice(0);
        this.domain = params.domain;
        this.context = params.context;
        return this._fetch(rowFields);
    },
    reload: function (handle, params) {
        params = params || {};
        if ('pagination' in params) {
            _.extend(this.context, params.pagination);
        }
        if ('range' in params) {
            this.currentRange = _.findWhere(this.ranges, {name: params.range});
        }
        //     get_full_context: function (ctx) {
//         var c = this._model.context(this.get('context'));
//         if (this.get('pagination_context')) {
//             c.add(this.get('pagination_context'));
//         }
//         // probably not ideal, needs to be kept in sync with arrows
//         if (this.get('range')) {
//             c.add({'grid_range': this.get('range')});
//         }
//         if (ctx) {
//             c.add(ctx);
//         }
//         return c;
        return this._fetch(this.gridData.groupBy);
    },

    // private API
    _fetch: function (rowFields) {
        var self = this;
        return this._rpc(this.modelName, 'read_grid')
            .kwargs({
                row_fields: rowFields,
                col_field: this.colField,
                cell_field: this.cellField,
                domain: this.domain,
                range: this.currentRange,
            })
            .withContext(this.context) // context: _this.get_full_context(),
            .exec()
            .then(function (result) {
                self.gridData = result;
                self.gridData.groupBy = rowFields;
                self.gridData.colField = self.colField;
                self.gridData.cellField = self.cellField;
                self.gridData.range = self.currentRange.name;
                self.gridData.context = self.context;
            });
    },
});

});
