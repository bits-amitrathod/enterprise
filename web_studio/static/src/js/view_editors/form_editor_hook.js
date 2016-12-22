odoo.define('web_studio.FormEditorHook', function (require) {
"use strict";

var Widget = require('web.Widget');

var FormEditorHook = Widget.extend({
    className: 'o_web_studio_hook',

    init: function(parent, position, hook_id, tagName) {
        this._super.apply(this, arguments);
        this.position = position;
        this.hook_id = hook_id;
        this.tagName = tagName || 'div';
    },
    start: function() {
        this.$el.data('hook_id', this.hook_id);

        var $content;
        switch (this.tagName) {
            case 'tr':
                $content = $('<td colspan="2">').append(this._render_span());
                break;
            default:
                $content = this._render_span();
                break;
        }
        this.$el.append($content);

        return this._super.apply(this, arguments);
    },
    _render_span: function() {
        return $('<span>').addClass('o_web_studio_hook_separator');
    },
});

return FormEditorHook;

});
