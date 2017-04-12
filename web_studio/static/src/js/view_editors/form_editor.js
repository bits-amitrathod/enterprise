odoo.define('web_studio.FormEditor', function (require) {
"use strict";

var core = require('web.core');
var FormRenderer = require('web.FormRenderer');

var EditorMixin = require('web_studio.EditorMixin');
var FormEditorHook = require('web_studio.FormEditorHook');

var _t = core._t;

var FormEditor =  FormRenderer.extend(EditorMixin, {
    nearest_hook_tolerance: 50,
    className: FormRenderer.prototype.className + ' o_web_studio_form_view_editor',
    events: _.extend({}, FormRenderer.prototype.events, {
        'click .o_web_studio_add_chatter': '_onAddChatter',
    }),
    custom_events: _.extend({}, FormRenderer.prototype.custom_events, {
        'on_hook_selected': '_onSelectedHook',
    }),
    /**
     * @constructor
     * @param {Object} params
     * @param {Boolean} params.show_invisible
     * @param {Boolean} params.chatter_allowed
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.show_invisible = params.show_invisible;
        this.chatter_allowed = params.chatter_allowed;
        this.silent = false;
        this.node_id = 1;
        this.hook_nodes = {};
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getLocalState: function () {
        var state = this._super.apply(this, arguments) || {};
        if (this.selected_node_id) {
            state.selected_node_id = this.selected_node_id;
        }
        return state;
    },
    /**
     * @override
     */
    highlightNearestHook: function ($helper, position) {
        var self = this;
        EditorMixin.highlightNearestHook.apply(this, arguments);

        var $nearest_form_hooks = this.$('.o_web_studio_hook')
            .touching({
                x: position.pageX - this.nearest_hook_tolerance,
                y: position.pageY - this.nearest_hook_tolerance,
                w: this.nearest_hook_tolerance*2,
                h: this.nearest_hook_tolerance*2})
            .nearest({x: position.pageX, y: position.pageY});

        var is_nearest_hook = false;
        $nearest_form_hooks.each(function () {
            var hook_id = $(this).data('hook_id');
            var hook = self.hook_nodes[hook_id];
            if ($($helper.context).data('structure') === 'notebook') {
                // a notebook cannot be placed inside a page
                if (hook.type !== 'page') {
                    is_nearest_hook = true;
                }
            } else {
                is_nearest_hook = true;
            }

            if (is_nearest_hook) {
                $(this).addClass('o_web_studio_nearest_hook');
                return false;
            }
        });

        return is_nearest_hook;
    },
    /**
     * @override
     */
    setLocalState: function (state) {
        this.silent = true;
        this._super.apply(this, arguments);
        this.unselectedElements();
        if (state.selected_node_id) {
            var $selected_node = this.$('[data-node-id="' + state.selected_node_id + '"]');
            if ($selected_node) {
                $selected_node.click();
            }
        }
        this.silent = false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _evaluateModifiers: function () {
        this._super.apply(this, arguments);
        if (this.show_invisible) {
            _.each(this.nodeModifiers, function (d) {
                if (d.$el.hasClass('o_form_invisible')) {
                    d.$el
                        .removeClass('o_form_invisible')
                        .addClass('o_web_studio_show_invisible');
                }
            });
        }
    },
    /**
     * Process a field node, in particular, bind an click handler on $el to edit
     * its field attributes.
     *
     * @private
     * @param {Object} node
     * @param {JQuery} $el
     */
    _processField: function (node, $el) {
        var self = this;
        // detect presence of mail fields
        if (node.attrs.name === "message_ids") {
            this.has_message_field = true;
        } else if (node.attrs.name === "message_follower_ids") {
            this.has_follower_field = true;
        } else {
            $el.attr('data-node-id', this.node_id++);
            $el.click(function (event) {
                event.preventDefault();
                event.stopPropagation();
                self.selected_node_id = $el.data('node-id');
                self.trigger_up('node_clicked', {node: node});
            });
            this.setSelectable($el);
        }
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        var self = this;
        this.has_chatter = false;
        this.has_follower_field = false;
        this.has_message_field = false;

        this.$el.droppable({
            accept: ".o_web_studio_component",
            drop: function (event, ui) {
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

        return this._super.apply(this, arguments).then(function () {
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
                var $buttonbox_hook = $('<button>')
                    .addClass('btn btn-sm oe_stat_button o_web_studio_button_hook')
                    .click(function(event) {
                        event.preventDefault();
                        self.trigger_up('view_change', {
                            type: 'add',
                            add_buttonbox: true,
                            structure: 'button',
                        });
                    });
                var $buttonbox = $('<div>')
                    .addClass('oe_button_box')
                    .append($buttonbox_hook);
                self.$('.o_form_sheet').prepend($buttonbox);
            }
        });
    },
    /**
     * @private
     * @returns {JQuery}
     */
    _renderAddingContentLine: function (node) {
        var formEditorHook = this._renderHook(node, 'after', 'tr');
        formEditorHook.appendTo($('<div>')); // start the widget
        return formEditorHook.$el;
    },
    /**
     * @override
     * @private
     */
    _renderButtonBox: function () {
        var self = this;
        var $buttonbox = this._super.apply(this, arguments);
        var $buttonhook = $('<button>').addClass('btn btn-sm oe_stat_button o_web_studio_button_hook');
        $buttonhook.click(function (event) {
            event.preventDefault();

            self.trigger_up('view_change', {
                type: 'add',
                structure: 'button',
            });
        });

        $buttonhook.prependTo($buttonbox);
        return $buttonbox;
    },
    /**
     * @override
     * @private
     */
    _renderFieldWidget: function (node) {
        var widget = this._super.apply(this, arguments);
        // make empty widgets appear if there is no label
        if (!widget.isSet() && (!node.has_label || node.attrs.nolabel)) {
            widget.$el.removeClass('o_form_field_empty').addClass('o_web_studio_widget_empty');
            widget.$el.text(widget.string);
        }
        return widget;
    },
    /**
     * @override
     * @private
     */
    _renderGenericTag: function (node) {
        var $result = this._super.apply(this, arguments);
        if (node.attrs.class === 'oe_title') {
            var formEditorHook = this._renderHook(node, 'after');
            formEditorHook.appendTo($result);
        }
        return $result;
    },
    /**
     * @override
     * @private
     */
    _renderInnerGroup: function (node) {
        var self = this;
        var formEditorHook;
        var $result = this._super.apply(this, arguments);
        // Add click event to see group properties in sidebar
        $result.attr('data-node-id', this.node_id++);
        $result.click(function (event) {
            event.stopPropagation();
            self.selected_node_id = $result.data('node-id');
            self.trigger_up('node_clicked', {node: node});
        });
        this.setSelectable($result);
        // Add hook for groups that have not yet content.
        if (!node.children.length) {
            formEditorHook = this._renderHook(node, 'inside', 'tr');
            formEditorHook.appendTo($result);
            this.setSelectable($result);
        } else {
            // Add hook before the first node in a group.
            formEditorHook = this._renderHook(node.children[0], 'before', 'tr');
            formEditorHook.appendTo($('<div>')); // start the widget
            $result.find("tr").first().before(formEditorHook.$el);
        }
        return $result;
    },
    /**
     * @override
     * @private
     */
    _renderInnerGroupLabel: function ($result, label, linked_node) {
        $result = this._super.apply(this, arguments);
        if (linked_node) {
            // We have to know if this field has a label or not.
            linked_node.has_label = true;
            var formEditorHook = this._renderHook(linked_node, 'after', 'tr');
            formEditorHook.appendTo($result);
        }
        return $result;
    },
    /**
     * @override
     * @private
     */
    _renderInnerGroupRow: function (nodes) {
        for (var i = 0; i < nodes.length; i++) {
            // we need to know if this field has a label or not
            nodes[i].has_label = true;
        }
        var $result = this._super.apply(this, arguments);

        // put hooks for each node in the group
        for (var j = 0; j < nodes.length; j++) {
            var node = nodes[j];
            if (!$result.find('.o_form_field').is('.o_form_invisible')) {
                // apply to the entire <tr> o_web_studio_show_invisible
                // rather then inner label/input
                if ($result.find('.o_form_field').hasClass('o_web_studio_show_invisible')) {
                    $result.find('.o_form_field, .o_form_label').removeClass('o_web_studio_show_invisible');
                    $result.addClass('o_web_studio_show_invisible');
                }
                // add hook only if field is visible
                $result = $result.add(this._renderAddingContentLine(node));
            }
            this._processField(node, $result.find('.o_td_label').parent());
        }
        return $result;
    },
    /**
     * @override
     * @private
     */
    _renderNode: function (node) {
        var self = this;
        var $el = this._super.apply(this, arguments);
        if (node.tag === 'div' && node.attrs.class === 'oe_chatter') {
            this.has_chatter = true;
            this.setSelectable($el);
            // Put a div in overlay preventing all clicks chatter's elements
            $el.append($('<div>', { 'class': 'o_web_studio_overlay' }));
            $el.attr('data-node-id', this.node_id++);
            $el.click(function () {
                self.selected_node_id = $el.data('node-id');
                self.trigger_up('node_clicked', {node: node});
            });
        }
        return $el;
    },
    /**
     * @override
     * @private
     */
    _renderStatButton: function (node) {
        var self = this;
        var $button = this._super.apply(this, arguments);
        $button.attr('data-node-id', this.node_id++);
        $button.click(function (ev) {
            if (! $(ev.target).closest('.o_form_field').length) {
                // click on the button and not on the field inside this button
                self.selected_node_id = $button.data('node-id');
                self.trigger_up('node_clicked', {node: node});
            }
        });
        this.setSelectable($button);
        return $button;
    },
    /**
     * @override
     * @private
     */
    _renderTabHeader: function (page) {
        var self = this;
        var $result = this._super.apply(this, arguments);
        $result.attr('data-node-id', this.node_id++);
        $result.click(function (event) {
            event.preventDefault();
            if (!self.silent) {
                self.selected_node_id = $result.data('node-id');
                self.trigger_up('node_clicked', {node: page});
            }
        });
        this.setSelectable($result);
        return $result;
    },
    /**
     * @override
     * @private
     */
    _renderTabPage: function (node) {
        var $result = this._super.apply(this, arguments);
        // Add hook only for pages that have not yet content.
        if (!$result.children().length) {
            var formEditorHook = this._renderHook(node, 'inside', 'div', 'page');
            formEditorHook.appendTo($result);
        }
        return $result;
    },
    /**
     * @override
     * @private
     */
    _renderTagField: function (node) {
        var $el = this._super.apply(this, arguments);
        this._processField(node, $el);
        return $el;
    },
    /**
     * @override
     * @private
     */
    _renderTagGroup: function (node) {
        var $result = this._super.apply(this, arguments);
        // Add hook after this group
        var formEditorHook = this._renderHook(node, 'after');
        formEditorHook.appendTo($('<div>')); // start the widget
        return $result.add(formEditorHook.$el);
    },
    /**
     * @override
     * @private
     */
    _renderTagNotebook: function (node) {
        var self = this;
        var $result = this._super.apply(this, arguments);

        var $addTag = $('<li>').append('<a href="#"><i class="fa fa-plus-square" aria-hidden="true"></a></i>');
        $addTag.click(function (event) {
            event.preventDefault();
            event.stopPropagation();
            self.trigger_up('view_change', {
                type: 'add',
                structure: 'page',
                node: node.children[node.children.length - 1], // Get last page in this notebook
            });
        });
        $result.find('ul.nav-tabs').append($addTag);

        var formEditorHook = this._renderHook(node, 'after');
        formEditorHook.appendTo($result);
        return $result;
    },
    /**
     * @override
     * @private
     */
    _renderTagSheet: function (node) {
        var $result = this._super.apply(this, arguments);
        var formEditorHook = this._renderHook(node, 'inside');
        formEditorHook.appendTo($result.find('.o_form_sheet'));
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @param {String} position
     * @param {String} tagName
     * @param {String} type
     * @returns {Widget} FormEditorHook
     */
    _renderHook: function (node, position, tagName, type) {
        var hook_id = _.uniqueId();
        this.hook_nodes[hook_id] = {
            node: node,
            position: position,
            type: type,
        };
        return new FormEditorHook(this, position, hook_id, tagName);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAddChatter: function () {
        // prevent multiple click
        $(event.currentTarget).css('pointer-events', 'none');
        this.trigger_up('view_change', {
            structure: 'chatter',
            remove_follower_ids: this.has_follower_field,
            remove_message_ids: this.has_message_field,
        });
    },
    /**
     * @private
     */
    _onButtonBoxHook: function () {
        this.trigger_up('view_change', {
            structure: 'buttonbox',
        });
    },
    /**
     * @private
     */
    _onSelectedHook: function () {
        this.selected_node_id = false;
    },
});

return FormEditor;

});
