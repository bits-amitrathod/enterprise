odoo.define('web_studio.XMLEditor', function (require) {
'use strict';

var ViewEditor = require('web_editor.ace');

/**
 * Extend the default view editor so that views are saved thanks to web studio and not
 * default RPC. Also notifies studio when the editor is closed.
 */
var XMLEditor = ViewEditor.extend({
    _saveView: function (session) {
        var def = $.Deferred();

        var view = this.views[session.id];
        var old_arch = view.arch;
        var new_arch = session.text;

        var self = this;
        this.trigger_up('save_xml_editor', {
            view_id: session.id,
            old_arch: old_arch,
            new_arch: new_arch,
            on_success: function () {
                self._toggleDirtyInfo(session.id, false);
                view.arch = new_arch;
                def.resolve();
            },
        });

        return def;
    },
    do_hide: function () {
        this.trigger_up("close_xml_editor");
        this._super.apply(this, arguments);
    },
});

return XMLEditor;

});
