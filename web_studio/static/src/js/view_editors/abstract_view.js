odoo.define('web_studio.AbstractViewEditor', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');

AbstractView.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    createStudioEditor: function (parent, Editor) {
        return this._createStudioRenderer(parent, Editor);
    },
    createStudioRenderer: function (parent) {
        var Renderer = this.config.Renderer;
        return this._createStudioRenderer(parent, Renderer);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _createStudioRenderer: function (parent, Renderer) {
        var self = this;
        var model = this.getModel(parent);
        return $.when(model.load(this.loadParams), this._loadLibs()).then(function (handle) {
            var state = model.get(handle);
            var params = _.extend({}, self.rendererParams, {
                // TODO: depend on each view
                mode: 'readonly',
                hasSelectors: false,
            });
            var editor = new Renderer(parent, state, params);

            model.setParent(editor);
            return editor;
        });
    },
});

});
