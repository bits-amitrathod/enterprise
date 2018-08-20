odoo.define('web_studio.ReportEditorAction', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var dom = require('web.dom');
var session = require('web.session');

var bus = require('web_studio.bus');
var ReportEditorManager = require('web_studio.ReportEditorManager');

var _t = core._t;

var ReportEditorAction = AbstractAction.extend({
    className: 'o_web_studio_client_action',
    custom_events: _.extend({}, AbstractAction.prototype.custom_events, {
        'open_record_form_view': '_onOpenRecordFormView',
        'studio_edit_report': '_onEditReport',
    }),
    /**
     * @override
     * @param {Object} options
     * @param {Object} options.report - a report datapoint
     */
    init: function (parent, context, options) {
        this._super.apply(this, arguments);

        this.set('title', _t("Report Editor"));
        this.handle = options.report;
        this.reportName = this.handle.data.report_name;

        this.studioActionEnv = options.studioActionEnv;
        this.env = {};
    },
    /**
     * @override
     */
    willStart: function () {
        var defs = [this._super.apply(this, arguments)];
        defs.push(this._readReport().then(this._loadEnvironment.bind(this)));
        return $.when.apply($, defs);
    },
    /**
     * @override
     */
    start: function () {
        var defs = [this._super.apply(this, arguments)];
        if (this.env.currentId) {
            defs.push(this._renderEditor());
        }
        else {
            this.do_warn(_t('Error: Preview not available because there is no existing record.'));
        }
        return $.when.apply($, defs);
    },
    /**
     * We need to use on_attach_callback because we need to the iframe to be
     * in the DOM to update it. Using on_reverse_breacrumb would have make more
     * sense but it's called too soon.
     *
     * @returns {Deferred}
     */
    on_attach_callback: function () {
        var isLoading = this.reportEditorManager.editorIframeDef;
        if (isLoading.state() === 'pending') {
            // this is the first rendering of the editor but we only want to
            // update the editor when going back with the breadcrumb
            return $.when();
        } else {
            return this.reportEditorManager.updateEditor();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} values
     * @returns {Deferred}
     */
    _editReport: function (values) {
        return this._rpc({
            route: '/web_studio/edit_report',
            params: {
                report_id: this.report.id,
                values: values,
                context: session.user_context,
            },
        });
    },
    /**
     * @private
     * @returns {Deferred<Object>}
     */
    _getReportViews: function () {
        var self = this;
        return this._rpc({
            route: '/web_studio/get_report_views',
            params: {
                record_id: this.env.currentId,
                report_name: this.reportName,
                context: session.user_context,
            },
        }).then(function (result) {
            self.reportViews = result;
        });
    },
    /**
     * Load and set the report environment.
     *
     * If the report is associated to the same model as the Studio action, the
     * action ids will be used ; otherwise a search on the report model will be
     * performed.
     *
     * @private
     * @returns {Deferred}
     */
    _loadEnvironment: function () {
        var self = this;
        this.env.modelName = this.report.model;

        if (this.studioActionEnv.modelName === this.report.model) {
            // we can use the ids coming from the action
            this.env.ids = this.studioActionEnv.ids;
        }

        var def;
        if (!this.env.ids || !this.env.ids.length) {
            def = this._rpc({
                model: self.report.model,
                method: 'search',
                args: [[]],
                context: session.user_context,
            }).then(function (result) {
                self.env.ids = result;
            });
        }
        return $.when(def).then(function () {
            self.env.currentId = self.env.ids && self.env.ids[0];
        });
    },
    /**
     * @private
     * @returns {Deferred}
     */
    _readReport: function () {
        var self = this;
        return self._rpc({
            model: 'ir.actions.report',
            method: 'read',
            args: [[self.handle.res_id]],
            context: session.user_context,
        }).then(function (result) {
            self.report = result[0];
        });
    },
    /**
     * @private
     * @returns {Deferred}
     */
    _readPaperFormat: function () {
        var self = this;
        return this._rpc({
            model: 'report.paperformat',
            method: 'read',
            args: [[this.report.paperformat_id[0]]],
            context: session.user_context,
        }).then(function (result) {
            self.paperFormat = result[0];
        });
    },
    /**
     * @private
     * @returns {Deferred}
     */
    _renderEditor: function () {
        var self = this;
        var defs = [this._getReportViews()];
        if (this.report.paperformat_id) {
            defs.push(this._readPaperFormat());
        }
        return $.when.apply($, defs).then(function () {
            var params = {
                paperFormat: self.paperFormat,
                report: self.report,
                reportHTML: self.reportViews.report_html,
                reportMainViewID: self.reportViews.main_view_id,
                reportViews: self.reportViews.views,
                env: self.env,
            };

            var oldEditor = self.reportEditorManager;
            self.reportEditorManager = new ReportEditorManager(self, params);

            var fragment = document.createDocumentFragment();
            return self.reportEditorManager.appendTo(fragment).then(function () {
                // dom is used to correctly call on_attach_callback
                dom.append(self.$el, [fragment], {
                    in_DOM: self.isInDOM,
                    callbacks: [{widget: self.reportEditorManager}],
                });
                if (oldEditor) {
                    oldEditor.destroy();
                }
            }).then(function () {
                bus.trigger('report_template_opened', self.report.name);
            });
        });
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onEditReport: function (ev) {
        var self = this;
        this._editReport(ev.data).then(function (result) {
            self.report = result[0];
            self._renderEditor();
        });
    },
    /**
     * @private
     */
    _onOpenRecordFormView: function () {
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'ir.actions.report',
            res_id: this.handle.res_id,
            views: [[false, 'form']],
            target: 'current',
        });
    },
});

core.action_registry.add('web_studio.action_edit_report', ReportEditorAction);

});
