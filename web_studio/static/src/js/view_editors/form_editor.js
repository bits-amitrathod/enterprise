odoo.define('web_studio.FormEditor', function (require) {
"use strict";

var core = require('web.core');

var FormRenderer = require('web.FormRenderer');
var FormEditorHook = require('web_studio.FormEditorHook');

var _t = core._t;

function _is_handled(event) {
    var $target = $(event.target);
    var $currentTarget = $(event.currentTarget);

    var $current = $target;
    while ($current[0] !== $currentTarget[0]) {
        if ($current.data('handle_studio_event')) {
            return true;
        }
        $current = $current.parent();
    }
    return false;
}

var FormEditor =  FormRenderer.extend({
    nearest_hook_tolerance: 50,
    className: FormRenderer.prototype.className + ' o_web_studio_form_view_editor',
    events: _.extend({}, FormRenderer.prototype.events, {
        'click .o_web_studio_add_chatter': function(event) {
            // prevent multiple click
            $(event.currentTarget).css('pointer-events', 'none');
            this.trigger_up('view_change', {
                structure: 'chatter',
                remove_follower_ids: this.has_follower_field,
                remove_message_ids: this.has_message_field,
            });
        },
        'click .o_web_studio_buttonbox_hook': function() {
            this.trigger_up('view_change', {
                structure: 'buttonbox',
            });
        }
    }),
    custom_events: _.extend({}, FormRenderer.prototype.custom_events, {
        'on_hook_selected': function() {
            this.selected_node_id = false;
        },
    }),
    init: function(parent, arch, fields, state, widgets_registry, options) {
        this._super.apply(this, arguments);
        this.show_invisible = options && options.show_invisible;
        this.chatter_allowed = options.chatter_allowed;
        this.silent = false;
        this.node_id = 1;
        this.hook_nodes = {};
    },
    _render: function() {
        var self = this;
        this.has_chatter = false;
        this.has_follower_field = false;
        this.has_message_field = false;

        this.$el.droppable({
            accept: ".o_web_studio_component",
            drop: function(event, ui) {
                var $hook = self.$('.o_web_studio_nearest_hook');
                if ($hook.length) {
                    var hook_id = $hook.data('hook_id');
                    var hook = self.hook_nodes[hook_id];

                    var values = {
                        type: 'add',
                        structure: ui.draggable.data('structure'),
                        field_description: ui.draggable.data('field_description'),
                        node: hook.node,
                        new_attrs: ui.draggable.data('new_attrs'),
                        position: hook.position,
                    };
                    ui.helper.removeClass('ui-draggable-helper-ready');
                    self.trigger_up('on_hook_selected');
                    self.trigger_up('view_change', values);
                }
            },
        });

        return this._super.apply(this, arguments).then(function() {
            // Add chatter hook
            if (!self.has_chatter && self.chatter_allowed) {
                var $chatter_hook = $('<div>')
                    .addClass('o_web_studio_add_chatter')
                    .append($('<span>', {
                        text: _t('Add Chatter Widget'),
                    }));
                $chatter_hook.insertAfter(self.$('.o_form_sheet'));
            }
            // Add buttonbox hook
            if (!self.$('.oe_button_box').length) {
                var $buttonbox_hook = $('<div>')
                    .addClass('o_web_studio_buttonbox_hook oe_button_box')
                    .append($('<span>', {
                        text: _t('Add a Button Box'),
                    }));
                self.$('.o_form_sheet').prepend($buttonbox_hook);
            }
        });
    },
    _render_node: function(node) {
        var self = this;
        var $el = this._super.apply(this, arguments);
        if (node.tag === 'div' && node.attrs.class === 'oe_chatter') {
            this.has_chatter = true;
            this._set_style_events($el);
            // Put a div in overlay preventing all clicks chatter's elements
            $el.append($('<div>', { 'class': 'o_web_studio_overlay' }));
            $el.attr('data-node-id', this.node_id++);
            $el.click(function() {
                self.selected_node_id = $el.data('node-id');
                self.trigger_up('node_clicked', {node: node});
            });
        }
        return $el;
    },
    _render_tag_sheet: function(node) {
        var $result = this._super.apply(this, arguments);
        var formEditorHook = this._render_hook(node, 'inside');
        formEditorHook.appendTo($result.find('.o_form_sheet'));
        return $result;
    },
    _render_generic_tag: function(node) {
        var $result = this._super.apply(this, arguments);
        if (node.attrs.class === 'oe_title') {
            var formEditorHook = this._render_hook(node, 'after');
            formEditorHook.appendTo($result);
        }
        return $result;
    },
    _render_tag_field: function(node) {
        var $el = this._super.apply(this, arguments);
        this._process_field(node, $el);
        return $el;
    },
    _render_field_widget: function(node) {
        var widget = this._super.apply(this, arguments);
        // make empty widgets appear if there is no label
        if (widget.$el.hasClass('o_form_field_empty') && (!node.has_label || node.attrs.nolabel)) {
            widget.$el.removeClass('o_form_field_empty').addClass('o_web_studio_widget_empty');
            widget.$el.text(widget.string);
        }
        return widget;
    },
    _render_tag_group: function(node) {
        var $result = this._super.apply(this, arguments);
        // Add hook after this group
        var formEditorHook = this._render_hook(node, 'after');
        formEditorHook.appendTo($('<div>')); // start the widget
        return $result.add(formEditorHook.$el);
    },
    _render_inner_group: function(node) {
        var self = this;
        var formEditorHook;
        var $result = this._super.apply(this, arguments);
        // Add click event to see group properties in sidebar
        $result.attr('data-node-id', this.node_id++);
        $result.click(function(event) {
            if (!_is_handled(event)) {
                self.selected_node_id = $result.data('node-id');
                self.trigger_up('node_clicked', {node: node});
            }
        });
        this._set_style_events($result);
        // Add hook for groups that have not yet content.
        if (!node.children.length) {
            formEditorHook = this._render_hook(node, 'inside', 'tr');
            formEditorHook.appendTo($result);
            this._set_style_events($result);
        } else {
            // Add hook before the first node in a group.
            formEditorHook = this._render_hook(node.children[0], 'before', 'tr');
            formEditorHook.appendTo($('<div>')); // start the widget
            $result.find("tr").first().before(formEditorHook.$el);
        }
        return $result;
    },
    _render_inner_group_label: function ($result, label, linked_node) {
        $result = this._super.apply(this, arguments);
        if (linked_node) {
            // We have to know if this field has a label or not.
            linked_node.has_label = true;
            var formEditorHook = this._render_hook(linked_node, 'after', 'tr');
            formEditorHook.appendTo($result);
        }
        return $result;
    },
    _render_adding_content_line: function (node) {
        var formEditorHook = this._render_hook(node, 'after', 'tr');
        formEditorHook.appendTo($('<div>')); // start the widget
        return formEditorHook.$el;
    },
    _render_inner_field: function(node) {
        // We have to know if this field has a label or not.
        node.has_label = true;
        var $result = this._super.apply(this, arguments);

        // Add hook only if field is visible
        if (!$result.find('.o_form_field').is('.o_form_invisible')) {
            $result = $result.add(this._render_adding_content_line(node));
        }

        this._process_field(node, $result.find('.o_td_label').parent());
        return $result;
    },
    _render_tag_notebook: function(node) {
        var self = this;
        var $result = this._super.apply(this, arguments);

        var $addTag = $('<li>').append('<a href="#"><i class="fa fa-plus-square" aria-hidden="true"></a></i>');
        $addTag.click(function(event) {
            event.preventDefault();
            event.stopPropagation();
            self.trigger_up('view_change', {
                type: 'add',
                structure: 'page',
                node: node.children[node.children.length - 1], // Get last page in this notebook
            });
        });
        $result.find('ul.nav-tabs').append($addTag);

        var formEditorHook = this._render_hook(node, 'after');
        formEditorHook.appendTo($result);
        return $result;
    },
    _render_tab_header: function(page) {
        var self = this;
        var $result = this._super.apply(this, arguments);
        $result.data('handle_studio_event', true);
        $result.attr('data-node-id', this.node_id++);
        $result.click(function(event) {
            event.preventDefault();
            if (!self.silent) {
                self.selected_node_id = $result.data('node-id');
                self.trigger_up('node_clicked', {node: page});
            }
        });
        this._set_style_events($result);
        return $result;
    },
    _render_tab_page: function(node) {
        var $result = this._super.apply(this, arguments);
        // Add hook only for pages that have not yet content.
        if (!$result.children().length) {
            var formEditorHook = this._render_hook(node, 'inside');
            formEditorHook.appendTo($result);
        }
        return $result;
    },
    _render_button_box: function() {
        var self = this;
        var $buttonbox = this._super.apply(this, arguments);
        var $buttonhook = $('<button>').addClass('btn btn-sm oe_stat_button o_web_studio_button_hook');
        $buttonhook.click(function(event) {
            event.preventDefault();

            self.trigger_up('view_change', {
                type: 'add',
                structure: 'button',
            });
        });

        $buttonhook.prependTo($buttonbox);
        return $buttonbox;
    },
    _render_stat_button: function(node) {
        var self = this;
        var $button = this._super.apply(this, arguments);
        $button.attr('data-node-id', this.node_id++);
        $button.click(function(ev) {
            if (! $(ev.target).closest('.o_form_field').length) {
                // click on the button and not on the field inside this button
                self.selected_node_id = $button.data('node-id');
                self.trigger_up('node_clicked', {node: node});
            }
        });
        this._set_style_events($button);
        return $button;
    },
    _handle_attributes: function($el) {
        this._super.apply(this, arguments);
        if (this.show_invisible && $el.hasClass('o_form_invisible')) {
            $el.removeClass('o_form_invisible').addClass('o_web_studio_show_invisible');
        }
    },
    _process_field: function(node, $el) {
        var self = this;
        // detect presence of mail fields
        if (node.attrs.name === "message_ids") {
            this.has_message_field = true;
        } else if (node.attrs.name === "message_follower_ids") {
            this.has_follower_field = true;
        } else {
            // bind handler on field clicked to edit field's attributes
            $el.attr('data-node-id', this.node_id++);
            $el.click(function(event) {
                event.preventDefault();
                event.stopPropagation();
                self.selected_node_id = $el.data('node-id');
                self.trigger_up('node_clicked', {node: node});
            });
            this._set_style_events($el);
        }
    },
    _set_style_events: function($el) {
        var self = this;
        $el.click(function() {
            self._reset_clicked_style();
            $(this).addClass('o_clicked');
        })
        .mouseover(function(event) {
            $(this).addClass('o_web_studio_hovered');
            event.stopPropagation();
        })
        .mouseout(function(event) {
            $(this).removeClass('o_web_studio_hovered');
            event.stopPropagation();
        });
    },
    _reset_clicked_style: function() {
        this.$('.o_clicked').removeClass('o_clicked');
    },
    _render_hook: function(node, position, tagName) {
        var hook_id = _.uniqueId();
        this.hook_nodes[hook_id] = {
            node: node,
            position: position,
        };
        return new FormEditorHook(this, position, hook_id, tagName);
    },
    highlight_nearest_hook: function(pageX, pageY) {
        this.$('.o_web_studio_nearest_hook').removeClass('o_web_studio_nearest_hook');
        var $nearest_form_hook = this.$('.o_web_studio_hook')
            .touching({
                x: pageX - this.nearest_hook_tolerance,
                y: pageY - this.nearest_hook_tolerance,
                w: this.nearest_hook_tolerance*2,
                h: this.nearest_hook_tolerance*2})
            .nearest({x: pageX, y: pageY}).eq(0);
        if ($nearest_form_hook.length) {
            $nearest_form_hook.addClass('o_web_studio_nearest_hook');
            return true;
        }
        return false;
    },
    get_local_state: function() {
        var state = this._super.apply(this, arguments);
        if (this.selected_node_id) {
            state.selected_node_id = this.selected_node_id;
        }
        return state;
    },
    set_local_state: function(state) {
        this.silent = true;
        this._super.apply(this, arguments);
        this._reset_clicked_style();
        if (state.selected_node_id) {
            var $selected_node = this.$('[data-node-id="' + state.selected_node_id + '"]');
            if ($selected_node) {
                $selected_node.click();
            }
        }
        this.silent = false;
    }
});

return FormEditor;

});
