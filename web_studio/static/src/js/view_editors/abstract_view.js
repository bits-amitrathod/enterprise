odoo.define('web_studio.AbstractViewEditor', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');

AbstractView.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Widget} parent
     * @param {Widget} Editor
     * @param {Object} options
     * @returns {Widget}
     */
    createStudioEditor: function (parent, Editor, options) {
        return this._createStudioRenderer(parent, Editor, options);
    },
    /**
     * @param {Widget} parent
     * @param {Widget} Editor
     * @returns {Widget}
     */
    createStudioRenderer: function (parent) {
        var Renderer = this.config.Renderer;
        return this._createStudioRenderer(parent, Renderer);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param {Widget} parent
     * @param {Widget} Renderer
     * @returns {Widget}
     */
    _createStudioRenderer: function (parent, Renderer, options) {
        var self = this;
        var model = this.getModel(parent);
        return $.when(
            model.load(this.loadParams),
            this._loadLibs()
        ).then(function (handle) {
            var state = model.get(handle);
            var params = _.extend({}, self.rendererParams, options);
            var editor = new Renderer(parent, state, params);

            model.setParent(editor);
            return editor;
        });
    },
});

});
