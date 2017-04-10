odoo.define('web_studio.KanbanEditor', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var KanbanRecordEditor = require('web_studio.KanbanRecordEditor');
var KanbanRenderer = require('web.KanbanRenderer');

var EditorMixin = require('web_studio.EditorMixin');

return KanbanRenderer.extend(EditorMixin, {
    className: KanbanRenderer.prototype.className + ' o_web_studio_kanban_view_editor',
    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        // only render one record
        this.state.data = this.state.data.slice(0, 1);
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            if (self.state.data.length === 0) {
                // add an empty record to be able to edit something
                var model = new BasicModel(self);
                return model.load({
                    fields: self.state.fields,
                    fieldsInfo: self.state.fieldsInfo,
                    modelName: self.state.model,
                    type: 'record',
                    viewType: self.state.viewType,
                }).then(function (record_id){
                    self.state.data.push(model.get(record_id));
                });
            }
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    highlightNearestHook: function ($helper, position) {
        if (this.kanban_record) {
            return this.kanban_record.highlightNearestHook($helper, position);
        }
    },
    /**
     * @override
     */
    getLocalState: function () {
        var state = this._super.apply(this, arguments) || {};
        if (this.kanban_record && this.kanban_record.selected_node_id) {
            state.selected_node_id = this.kanban_record.selected_node_id;
        }
        return state;
    },
    /**
     * @override
     */
    setLocalState: function (state) {
        if (this.kanban_record) {
            this.kanban_record.setLocalState(state);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Deferred}
     */
    _render: function () {
        var is_grouped = !!this.arch.attrs.default_group_by;
        this.$el.toggleClass('o_kanban_grouped', is_grouped);
        this.$el.toggleClass('o_kanban_ungrouped', !is_grouped);

        this.$el.empty();
        var fragment = document.createDocumentFragment();
        this._renderUngrouped(fragment);

        if (is_grouped) {
            var $group = $('<div>', {class: 'o_kanban_group'});
            $group.append(fragment);
            this.$el.append($group);

            // render a second empty column
            var fragment_empty = document.createDocumentFragment();
            this._renderDemoDivs(fragment_empty, 7);
            this._renderGhostDivs(fragment_empty, 6);
            var $group_empty = $('<div>', {class: 'o_kanban_group'});
            $group_empty.append(fragment_empty);
            this.$el.append($group_empty);
        } else {
            this.$el.append(fragment);
        }
        return $.when();
    },
    /**
     * Renders empty demo divs in a document fragment.
     *
     * @private
     * @param {DocumentFragment} fragment
     * @param {integer} nbDivs the number of divs to append
     */
    _renderDemoDivs: function (fragment, nbDivs) {
        for (var i = 0, demo_div; i < nbDivs; i++) {
            demo_div = $("<div>").addClass("o_kanban_record o_kanban_demo");
            demo_div.appendTo(fragment);
        }
    },
    /**
     * @private
     * @param {DocumentFragment} fragment
     */
    _renderUngrouped: function (fragment) {
        // overwrite this method to use the KanbanRecordEditor
        var self = this;
        _.each(this.state.data, function (record) {
            var is_dashboard = self.$el.hasClass('o_kanban_dashboard');
            self.kanban_record = new KanbanRecordEditor(self, record, self.recordOptions, is_dashboard);
            self.widgets.push(self.kanban_record);
            self.kanban_record.appendTo(fragment);
        });
        this._renderDemoDivs(fragment, 6);
        this._renderGhostDivs(fragment, 6);
    },
});

});
