odoo.define('web_studio.ListEditor', function (require) {
"use strict";

var ListRenderer = require('web.BasicListRenderer');

return ListRenderer.extend({
    nearest_hook_tolerance: 50,
    className: ListRenderer.prototype.className + ' o_web_studio_list_view_editor',
    events: _.extend({}, ListRenderer.prototype.events, {
        'click th:not(.o_web_studio_hook), td:not(.o_web_studio_hook)': 'on_existing_column',
    }),

    init: function(parent, arch, fields, state, widgets_registry, options) {
        this._super.apply(this, arguments);
        if (options && options.show_invisible) {
            this.invisible_columns = _.difference(this.arch.children, this.columns);
            this.columns = this.arch.children;
        } else {
            this.invisible_columns = [];
        }
        this.node_id = 1;
    },

    _render: function() {
        var self = this;
        var def = this._super.apply(this, arguments);

        this.$el.droppable({
            accept: ".o_web_studio_component",
            drop: function(event, ui) {
                var $hook = self.$('.o_web_studio_nearest_hook');
                if ($hook.length) {
                    var position = $hook.closest('table').find('th').eq($hook.index()).data('position') || 'after';
                    var hooked_field_index = position === 'before' && $hook.index() + 1 || $hook.index() - 1;
                    var field_name = $hook.closest('table').find('th').eq(hooked_field_index).data('name');
                    var node = _.find(self.columns, function (column) {
                        return column.attrs.name === field_name;
                    });
                    self.selected_node_id = false;

                    var values = {
                        type: 'add',
                        structure: ui.draggable.data('structure'),
                        field_description: ui.draggable.data('field_description'),
                        node: node,
                        new_attrs: ui.draggable.data('new_attrs'),
                        position: position,
                    };
                    ui.helper.removeClass('ui-draggable-helper-ready');
                    self.trigger_up('on_hook_selected');
                    self.trigger_up('view_change', values);
                }
            },
        });

        // HOVER
        this.$('th, td').not('.o_web_studio_hook').hover(function(ev) {
            var $el = $(ev.currentTarget);
            self.$('.o_hover').removeClass('o_hover');

            // add style on hovered column
            $el.closest('table')
                .find('tr')
                .children(':nth-child(' + ($el.index() + 1) + ')')
                .addClass('o_hover');
        });
        this.$('table').mouseleave(function() {
            self.$('.o_hover').removeClass('o_hover');
        });

        // CLICK
        this.$('th, td').click(function(ev) {
            var $el = $(ev.currentTarget);
            self.$('.o_clicked').removeClass('o_clicked');

            $el.closest('table')
                .find('tr')
                .children(':nth-child(' + ($el.index() + 1) + ')')
                .addClass('o_clicked');
        });

        return def;
    },

    _render_header: function() {
        var $header = this._super.apply(this, arguments);
        var self = this;
        _.each($header.find('th'), function(th, index) {
            var $new_th = $('<th>')
                .addClass('o_web_studio_hook')
                .append(
                    $('<i>').addClass('fa fa-plus')
            );
            $new_th.insertAfter($(th));

            // Insert a hook before the first column
            if (index === 0) {
                var $new_th_before = $('<th>')
                    .addClass('o_web_studio_hook')
                    .data('position', 'before')
                    .append(
                        $('<i>').addClass('fa fa-plus')
                );
                $new_th_before.insertBefore($(th));
            }
            $(th).attr('data-node-id', self.node_id++);
        });
        return $header;
    },

    _render_header_cell: function(node) {
        var $th = this._super.apply(this, arguments);
        if (_.contains(this.invisible_columns, node)) {
            $th.addClass('o_web_studio_show_invisible');
        }
        return $th;
    },

    _render_empty_row: function() {
        var $row = this._super.apply(this, arguments);
        _.each($row.find('td'), function(td, index) {
            $('<td>')
                .addClass('o_web_studio_hook')
                .insertAfter($(td));

            // Insert a hook before the first column
            if (index === 0) {
                $('<td>')
                    .addClass('o_web_studio_hook')
                    .insertBefore($(td));

            }
        });
        return $row;
    },

    _render_row: function() {
        var $row = this._super.apply(this, arguments);
        _.each($row.find('td'), function(td, index) {
            $('<td>')
                .addClass('o_web_studio_hook')
                .insertAfter($(td));

            // Insert a hook before the first column
            if (index === 0) {
                $('<td>')
                    .addClass('o_web_studio_hook')
                    .insertBefore($(td));

            }
        });
        return $row;
    },

    _render_footer: function() {
        var $footer = this._super.apply(this, arguments);
        _.each($footer.find('td'), function(td, index) {
            $('<td>')
                .addClass('o_web_studio_hook')
                .insertAfter($(td));

            // Insert a hook before the first column
            if (index === 0) {
                $('<td>')
                    .addClass('o_web_studio_hook')
                    .insertBefore($(td));

            }
        });
        return $footer;

    },
    highlight_nearest_hook: function(pageX, pageY) {
        this.$('.o_web_studio_nearest_hook').removeClass('o_web_studio_nearest_hook');
        var $nearest_list_hook = this.$('.o_web_studio_hook')
            .touching({
                x: pageX - this.nearest_hook_tolerance,
                y: pageY - this.nearest_hook_tolerance,
                w: this.nearest_hook_tolerance*2,
                h: this.nearest_hook_tolerance*2})
            .nearest({x: pageX, y: pageY}).eq(0);
        if ($nearest_list_hook.length) {
            $nearest_list_hook.closest('table')
                .find('tr')
                .children(':nth-child(' + ($nearest_list_hook.index() + 1) + ')')
                .addClass('o_web_studio_nearest_hook');
            return true;
        }
        return false;
    },
    on_existing_column: function(ev) {
        var $el = $(ev.currentTarget);
        var $selected_column = $el.closest('table').find('th').eq($el.index());

        var field_name = $selected_column.data('name');
        var node = _.find(this.columns, function (column) {
            return column.attrs.name === field_name;
        });
        this.selected_node_id = $selected_column.data('node-id');
        this.trigger_up('node_clicked', {node: node});
    },

    get_local_state: function() {
        var state = this._super.apply(this, arguments);
        if (this.selected_node_id) {
            state.selected_node_id = this.selected_node_id;
        }
        return state;
    },

    set_local_state: function(state) {
        if (state.selected_node_id) {
            var $selected_node = this.$('th[data-node-id="' + state.selected_node_id + '"]');
            if ($selected_node) {
                $selected_node.click();
            }
        }
    },

});

});
