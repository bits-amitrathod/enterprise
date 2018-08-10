odoo.define('documents.DocumentsKanbanRenderer', function (require) {
"use strict";

/**
 * This file defines the Renderer for the Documents Kanban view, which is an
 * override of the KanbanRenderer.
 */

var DocumentsKanbanRecord = require('documents.DocumentsKanbanRecord');

var KanbanRenderer = require('web.KanbanRenderer');

var DocumentsKanbanRenderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord: DocumentsKanbanRecord,
    }),
    custom_events: _.extend({}, KanbanRenderer.prototype.custom_events, {
        select_record: '_onRecordSelected',
    }),

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.anchorID = null; // used to select records with crl/shift keys
        this.selectedRecordIDs = [];
    },
    /**
     * @override
     */
    start: function () {
        this.$el.addClass('o_documents_kanban_view position-relative align-content-start flex-grow-1 flex-shrink-1');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    updateState: function () {
        var self = this;
        this.anchorID = null;
        return this._super.apply(this, arguments).then(function () {
            self._updateSelection();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateSelection: function () {
        var self = this;
        var hasSelection = false;
        _.each(this.widgets, function (widget) {
            var selected = _.contains(self.selectedRecordIDs, widget.getResID());
            widget.updateSelection(selected);
            hasSelection = hasSelection || selected;
        });
        this.$el.toggleClass('o_documents_kanban_view_has_selection', hasSelection);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * React to records selection changes to update the DocumentInspector with
     * the current selected records.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {boolean} ev.data.clear if true, unselect other records
     * @param {MouseEvent} ev.data.originalEvent the event catched by the child
     *   element triggering up the OdooEvent
     * @param {string} ev.data.resID the resID of the record updating its status
     * @param {boolean} ev.data.selected whether the record is selected or not
     */
    _onRecordSelected: function (ev) {
        ev.stopPropagation();

        // update the list of selected records (support typical behavior of
        // ctrl/shift/command muti-selection)
        var shift = ev.data.originalEvent.shiftKey;
        var ctrl = ev.data.originalEvent.ctrlKey || ev.data.originalEvent.metaKey;
        if (ev.data.clear || shift || ctrl) {
            if (this.selectedRecordIDs.length === 1 && this.selectedRecordIDs[0] === ev.data.resID) {
                // unselect the record if it is currently the only selected one
                this.selectedRecordIDs = [];
            } else if (shift && this.selectedRecordIDs.length) {
                var recordIDs = this.state.res_ids;
                var anchorIndex = recordIDs.indexOf(this.anchorID);
                var selectedRecordIndex = recordIDs.indexOf(ev.data.resID);
                var lowerIndex = Math.min(anchorIndex, selectedRecordIndex);
                var upperIndex = Math.max(anchorIndex, selectedRecordIndex);
                var shiftSelection = recordIDs.slice(lowerIndex, upperIndex + 1);
                if (ctrl) {
                    this.selectedRecordIDs = _.uniq(this.selectedRecordIDs.concat(shiftSelection));
                } else {
                    this.selectedRecordIDs = shiftSelection;
                }
            } else if (ctrl && this.selectedRecordIDs.length) {
                var oldIds = this.selectedRecordIDs.slice();
                this.selectedRecordIDs = _.without(this.selectedRecordIDs, ev.data.resID);
                if (this.selectedRecordIDs.length === oldIds.length) {
                    this.selectedRecordIDs.push(ev.data.resID);
                    this.anchorID = ev.data.resID;
                }
            } else {
                this.selectedRecordIDs = [ev.data.resID];
                this.anchorID = ev.data.resID;
            }
        } else if (ev.data.selected) {
            this.selectedRecordIDs.push(ev.data.resID);
            this.selectedRecordIDs = _.uniq(this.selectedRecordIDs);
            this.anchorID = ev.data.resID;
        } else {
            this.selectedRecordIDs = _.without(this.selectedRecordIDs, ev.data.resID);
        }

        // notify the controller of the selection changes
        this.trigger_up('selection_changed', {
            selection: this.selectedRecordIDs,
        });

        // update the kanban records
        this._updateSelection();
    },
});

return DocumentsKanbanRenderer;

});
