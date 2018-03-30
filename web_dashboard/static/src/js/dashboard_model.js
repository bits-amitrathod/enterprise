odoo.define('web_dashboard.DashboardModel', function (require) {
"use strict";

/**
 * This module defines the DashboardModel, an extension of the BasicModel.
 * Unlike the BasicModel, the DashboardModel only keep a single dataPoint (there
 * is no relational data in this model), and this dataPoint contains two
 * additional keys: aggregates and formulas, which gather the information
 * about the <aggregate> and <formula> occurrences in the dashboard arch.
 */

var BasicModel = require('web.BasicModel');
var Domain = require('web.Domain');
var pyeval = require('web.pyeval');

var DashboardModel = BasicModel.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    load: function (params) {
        params.type = 'record';
        this.dataPoint = this._makeDataPoint(params);
        return this._load(this.dataPoint);
    },
    /**
     * @override
     */
    reload: function (id, options) {
        options = options || {};
        if (options.domain !== undefined) {
            this.dataPoint.domain = options.domain;
        }
        return this._load(this.dataPoint);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Evaluates formulas of the dataPoint with its values.
     *
     * @private
     * @param {Object} dataPoint
     */
    _evaluateFormulas: function (dataPoint) {
        _.each(dataPoint.formulas, function (formula, formulaID) {
            try {
                dataPoint.data[formulaID] = pyeval.py_eval(formula.value, {
                    record: dataPoint.data,
                });
                if (!isFinite(dataPoint.data[formulaID])) {
                    dataPoint.data[formulaID] = NaN;
                }
            } catch (e) {
                dataPoint.data[formulaID] = NaN;
            }
        });
    },
    /**
     * @override
     * @private
     */
    _load: function (dataPoint) {
        var self = this;

        var domainMapping = {};
        var fieldsInfo = dataPoint.fieldsInfo.dashboard;
        _.each(dataPoint.aggregates, function (aggregateName) {
            var domain = fieldsInfo[aggregateName].domain;
            if (domain in domainMapping) {
                domainMapping[domain].push(aggregateName);
            } else {
                domainMapping[domain] = [aggregateName];
            }
        });

        var defs = _.map(domainMapping, function (aggregateNames, domain) {
            var fieldNames = _.map(aggregateNames, function (aggregateName) {
                var fieldName = fieldsInfo[aggregateName].field;
                var groupOperator = fieldsInfo[aggregateName].group_operator;
                return aggregateName + ':' + groupOperator + '(' + fieldName + ')';
            });
            return self._rpc({
                context: dataPoint.getContext(),
                domain: dataPoint.domain.concat(new Domain(domain).toArray()),
                fields: fieldNames,
                groupBy: [],
                lazy: true,
                method: 'read_group',
                model: dataPoint.model,
                orderBy: [],
            }).then(function (result) {
                result = result[0];
                _.each(aggregateNames, function (aggregateName) {
                    dataPoint.data[aggregateName] = result[aggregateName] || 0;
                });
            });
        });

        return $.when.apply($, defs).then(function () {
            self._evaluateFormulas(dataPoint);
            return dataPoint.id;
        });
    },
    /**
     * @override
     * @private
     */
    _makeDataPoint: function (params) {
        var dataPoint = this._super.apply(this, arguments);
        dataPoint.aggregates = params.aggregates;
        dataPoint.formulas = params.formulas;
        return dataPoint;
    },
});

return DashboardModel;

});
