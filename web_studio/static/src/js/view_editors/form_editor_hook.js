odoo.define('web_studio.FormEditorHook', function (require) {
"use strict";

var Widget = require('web.Widget');

var FormEditorHook = Widget.extend({
    className: 'o_web_studio_hook',

    init: function(parent, tag, position, hook_id) {
        this._super.apply(this, arguments);
        this.tag = tag;
        this.position = position;
        this.hook_id = hook_id;
        if (this.tag === 'field' || (this.tag === 'group' && position === 'inside')) {
            this.tagName = 'tr';
        }
    },
    start: function() {
        this.$el.data('hook_id', this.hook_id);

        var $content;
        switch (this.tag) {
            case 'field':
                $content = $('<td colspan="2">').append(this._render_span());
                break;
            case 'group':
                if (this.position === 'inside') {
                    $content = $('<td colspan="2">').append(this._render_span());
                } else {
                    $content = this._render_span();
                }
                break;
            case 'page':
                this.$el.css({padding: '25px'});
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
