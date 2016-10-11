odoo.define('web_studio.FormEditorHook', function (require) {
"use strict";

var Widget = require('web.Widget');

var FormEditorHook = Widget.extend({
    className: 'o_web_studio_new_line',

    init: function(parent, node, position) {
        this._super.apply(this, arguments);
        this.node = node;
        this.position = position;
        if (this.node.tag === 'field' || (this.node.tag === 'group' && position === 'inside')) {
            this.tagName = 'tr';
        }
    },
    start: function() {
        var self = this;
        var $content;
        switch (this.node.tag) {
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

        this.$el.droppable({
            accept: ".o_web_studio_component",
            hoverClass : "o_web_studio_hovered",
            drop: function(event, ui) {
                var values = {
                    type: 'add',
                    structure: ui.draggable.data('structure'),
                    field_description: ui.draggable.data('field_description'),
                    node: self.node,
                    new_attrs: ui.draggable.data('new_attrs'),
                    position: self.position,
                };
                ui.helper.removeClass('ui-draggable-helper-ready');
                self.trigger_up('on_hook_selected');
                self.trigger_up('view_change', values);
            },
            over: function(event, ui) {
                ui.helper.addClass('ui-draggable-helper-ready');
            },
            out: function(event, ui) {
                ui.helper.removeClass('ui-draggable-helper-ready');
            }
        });

        return this._super.apply(this, arguments);
    },
    _render_span: function() {
        return $('<span>').addClass('o_web_studio_new_line_separator');
    },
});

return FormEditorHook;

});
