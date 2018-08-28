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

    setSelectedRecordIDs: function (selectedRecordIDs) {
        this.selectedRecordIDs = selectedRecordIDs;
    },

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
        _.each(this.widgets, function (widget) {
            var selected = _.contains(self.selectedRecordIDs, widget.getResID());
            widget.updateSelection(selected);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

});

return DocumentsKanbanRenderer;

});
