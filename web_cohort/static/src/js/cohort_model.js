odoo.define('web_cohort.CohortModel', function (require) {
'use strict';

var AbstractModel = require('web.AbstractModel');

var CohortModel = AbstractModel.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
    * @override
    * @returns {Object}
    */
    get: function () {
      return this.data;
    },
    /**
     * @override
     * @param {Object} params
     * @param {string} params.modelName
     * @param {string} params.dateStart
     * @param {string} params.dateStop
     * @param {string} params.measure
     * @param {string} params.interval
     * @param {Array[]} params.domain
     * @returns {Deferred}
     */
    load: function (params) {
        this.modelName = params.modelName;
        this.dateStart = params.dateStart;
        this.dateStop = params.dateStop;
        this.measure = params.measure;
        this.interval = params.interval;
        this.domain = params.domain;
        this.data = {
            measure: this.measure,
            interval: this.interval,
        };
        return this._fetchData();
    },
    /**
     * Reload data.
     *
     * @param {any} handle
     * @param {Object} params
     * @param {string} params.measure
     * @param {string} params.interval
     * @param {Array[]} params.domain
     * @returns {Deferred}
     */
    reload: function (handle, params) {
        if ('measure' in params) {
            this.data.measure = params.measure;
        }
        if ('interval' in params) {
            this.data.interval = params.interval;
        }
        if ('domain' in params) {
            this.domain = params.domain;
        }
        return this._fetchData();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetch cohort data.
     *
     * @private
     * @returns {Deferred}
     */
    _fetchData: function () {
        var self = this;
        return this._rpc({
            model: this.modelName,
            method: 'get_cohort_data',
            kwargs: {
                date_start: this.dateStart,
                date_stop: this.dateStop,
                measure: this.data.measure,
                interval: this.data.interval,
                domain: this.domain,
            }
        }).then(function (result) {
            self.data.report = result;
        });
    },
});

return CohortModel;

});
