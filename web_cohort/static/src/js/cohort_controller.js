odoo.define('web_cohort.CohortController', function (require) {
'use strict';

var AbstractController = require('web.AbstractController');
var config = require('web.config');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var framework = require('web.framework');
var session = require('web.session');

var qweb = core.qweb;

var CohortController = AbstractController.extend({
    custom_events: _.extend({}, AbstractController.prototype.custom_events, {
        'row_clicked': '_onRowClicked',
    }),
    /**
     * @override
     * @param {Widget} parent
     * @param {CohortModel} model
     * @param {CohortRenderer} renderer
     * @param {Object} params
     * @param {string} params.modelName
     * @param {string} params.title
     * @param {Object} params.measures
     * @param {Object} params.intervals
     * @param {string} params.dateStartString
     * @param {string} params.dateStopString
     * @param {Array[]} params.views
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.title = params.title;
        this.measures = params.measures;
        this.intervals = params.intervals;
        this.dateStartString = params.dateStartString;
        this.dateStopString = params.dateStopString;
        this.views = params.views;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the current mode, measure and groupbys, so we can restore the
     * view when we save the current state in the search view, or when we add it
     * to the dashboard.
     *
     * @override
     * @returns {Object}
     */
    getContext: function () {
        var state = this.model.get();
        return {
            cohort_measure: state.measure,
            cohort_interval: state.interval,
        };
    },

    /**
     * @override
     * @param {jQueryElement} $node
     */
    renderButtons: function ($node) {
        if ($node) {
            this.$buttons = $(qweb.render('CohortView.buttons', {
                measures: this.measures,
                intervals: this.intervals,
                isMobile: config.device.isMobile
            }));
            this.$measureList = this.$buttons.find('.o_cohort_measures_list');
            this.$buttons.appendTo($node);
            this._updateButtons();
            this.$buttons.click(this._onButtonClick.bind(this));
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Export cohort data in Excel file
     *
     * @private
     */
    _downloadExcel: function () {
        var data = this.model.get();
        data = _.extend(data, {
            title: this.title,
            interval_string: this.intervals[data.interval],
            measure_string: this.measures[data.measure] || 'Count',
            date_start_string: this.dateStartString,
            date_stop_string: this.dateStopString,
        });
        framework.blockUI();
        session.get_file({
            url: '/web/cohort/export',
            data: {data: JSON.stringify(data)},
            complete: framework.unblockUI,
            error: crash_manager.rpc_error.bind(crash_manager)
        });
    },
    /**
     * @private
     * @param {string} interval
     */
    _setInterval: function (interval) {
      this.update({interval: interval});
    },
    /**
     * @private
     * @param {string} measure should be a valid (and aggregatable) field name
     */
    _setMeasure: function (measure) {
        this.update({measure: measure});
    },
    /**
     * @override
     * @private
     * @returns {Deferred}
     */
    _update: function () {
      this._updateButtons();
      return this._super.apply(this, arguments);
    },
    /**
     * makes sure that the buttons in the control panel matches the current
     * state (so, correct active buttons and stuff like that)
     *
     * @private
     */
    _updateButtons: function () {
        if (!this.$buttons) {
            return;
        }
        var data = this.model.get();
        // Hide download button if no cohort data
        this.$buttons.find('.o_cohort_download_button').toggleClass('hidden', !data.report.rows.length);
        if (config.device.isMobile) {
            var $activeInterval = this.$buttons
                .find('.o_cohort_interval_button[data-interval="' + data.interval + '"]');
            this.$buttons.find('.dropdown_cohort_content').text($activeInterval.text());
        }
        this.$buttons.find('.o_cohort_interval_button').removeClass('active');
        this.$buttons
            .find('.o_cohort_interval_button[data-interval="' + data.interval + '"]')
            .addClass('active');
        this.$measureList.find('li').each(function () {
            var $li = $(this);
            $li.toggleClass('selected', $li.data('field') === data.measure);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Do what need to be done when a button from the control panel is clicked.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onButtonClick: function (event) {
        var $target = $(event.target);
        if ($target.hasClass('o_cohort_interval_button')) {
            this._setInterval($target.data('interval'));
        } else if ($target.hasClass('o_cohort_download_button')) {
            this._downloadExcel();
        } else if ($target.parents('.o_cohort_measures_list').length) {
            event.preventDefault();
            event.stopPropagation();
            var $parent = $target.parent();
            var field = $parent.data('field');
            this._setMeasure(field);
        }
    },
    /**
     * Open view when clicked on row
     *
     * @private
     * @param {OdooEvent} event
     */
    _onRowClicked: function (event) {
        this.do_action({
            type: 'ir.actions.act_window',
            name: this.title,
            res_model: this.modelName,
            views: this.views,
            domain: event.data.domain,
        });
    },
});

return CohortController;

});
