odoo.define('web_cohort.CohortRenderer', function (require) {
'use strict';

var AbstractRenderer = require('web.AbstractRenderer');
var core = require('web.core');

var qweb = core.qweb;

var CohortRenderer = AbstractRenderer.extend({
    events: _.extend({}, AbstractRenderer.prototype.events, {
        'click .o_cohort_row_clickable': '_onClickRow',
    }),
    /**
     * @override
     * @param {Widget} parent
     * @param {Object} state
     * @param {Object} params
     * @param {Object} params.measures
     * @param {Object} params.intervals
     * @param {string} params.dateStartString
     * @param {string} params.dateStopString
     * @param {string} params.mode
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.measures = params.measures;
        this.intervals = params.intervals;
        this.dateStartString = params.dateStartString;
        this.dateStopString = params.dateStopString;
        this.mode = params.mode;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @returns {Deferred}
     */
    _render: function () {
        this.$el.empty().append(qweb.render('CohortView', {
            report: this.state.report,
            measure: this.measures[this.state.measure],
            interval: this.intervals[this.state.interval],
            date_start_string: this.dateStartString,
            date_stop_string: this.dateStopString,
            mode: this.mode,
        }));
        this.$('.o_cohort_value').tooltip();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickRow: function (event) {
        if (!$(event.target).hasClass('o_cohort_value')) {
            return;
        }
        var rowIndex = $(event.currentTarget).data().row;
        var colIndex = $(event.target).data().col;
        var row = this.state.report.rows[rowIndex];
        var rowDomain = row ? row.domain : [];
        var cellContent = row ? row.columns[colIndex] : false;
        var cellDomain = cellContent ? cellContent.domain : [];

        var fullDomain = rowDomain.concat(cellDomain);
        if (cellDomain.length) {
            fullDomain.unshift('&', '&');
        }
        if (fullDomain.length) {
            this.trigger_up('row_clicked', {domain: fullDomain});
        }
    },
});

return CohortRenderer;

});
