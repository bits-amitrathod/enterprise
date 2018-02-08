odoo.define('web_studio.ListEditor', function (require) {
"use strict";

var ListRenderer = require('web.ListRenderer');
var EditorMixin = require('web_studio.EditorMixin');

return ListRenderer.extend(EditorMixin, {
    nearest_hook_tolerance: 200,
    className: ListRenderer.prototype.className + ' o_web_studio_list_view_editor',
    events: _.extend({}, ListRenderer.prototype.events, {
        'click th:not(.o_web_studio_hook), td:not(.o_web_studio_hook)': '_onExistingColumn',
    }),
    /**
     * @constructor
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        if (params.show_invisible) {
            this.invisible_columns = _.difference(this.arch.children, this.columns);
            this.columns = this.arch.children;
        } else {
            this.invisible_columns = [];
        }
        this.node_id = 1;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getLocalState: function() {
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
        EditorMixin.highlightNearestHook.apply(this, arguments);

        var $nearest_list_hook = this.$('.o_web_studio_hook')
            .touching({
                x: position.pageX - this.nearest_hook_tolerance,
                y: position.pageY - this.nearest_hook_tolerance,
                w: this.nearest_hook_tolerance*2,
                h: this.nearest_hook_tolerance*2})
            .nearest({x: position.pageX, y: position.pageY}).eq(0);
        if ($nearest_list_hook.length) {
            var $elements = this._getColumnElements($nearest_list_hook);
            $elements.addClass('o_web_studio_nearest_hook');
            return true;
        }
        return false;
    },
    /**
     * @override
     */
    setLocalState: function(state) {
        if (state.selected_node_id) {
            var $selected_node = this.$('th[data-node-id="' + state.selected_node_id + '"]');
            if ($selected_node) {
                $selected_node.click();
            }
        }
    },
    /**
     * In the list editor, we want to select the whole column, not only a single
     * cell.
     *
     * @override
     */
    setSelectable: function ($el) {
        EditorMixin.setSelectable.apply(this, arguments);

        var self = this;
        $el.click(function (ev) {
            var $target = $(ev.currentTarget);
            self.$('.o_web_studio_clicked').removeClass('o_web_studio_clicked');
            var $elements = self._getColumnElements($target);
            $elements.addClass('o_web_studio_clicked');
        })
        .mouseover(function (ev) {
            if (self.$('.ui-draggable-dragging').length) {
                return;
            }
            var $target = $(ev.currentTarget);
            var $elements = self._getColumnElements($target);
            $elements.addClass('o_web_studio_hovered');
        })
        .mouseout(function () {
            self.$('.o_web_studio_hovered').removeClass('o_web_studio_hovered');
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get all elements associated to a table column.
     *
     * @private
     * @param {jQuery} $target
     * @returns {jQuery}
     */
    _getColumnElements: function ($target) {
        return $target.closest('table')
            .find('tr')
            .children(':nth-child(' + ($target.index() + 1) + ')');
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        var self = this;
        var def = this._super.apply(this, arguments);

        this.$el.droppable({
            accept: ".o_web_studio_component",
            drop: function (event, ui) {
                var $hook = self.$('.o_web_studio_nearest_hook');
                if ($hook.length) {
                    var position = $hook.closest('table').find('th').eq($hook.index()).data('position') || 'after';
                    var hooked_field_index = position === 'before' && $hook.index() + 1 || $hook.index() - 1;
                    var field_name = $hook.closest('table').find('th').eq(hooked_field_index).data('name');
                    var node = _.find(self.columns, function (column) {
                        return column.attrs.name === field_name;
                    });
                    // When there is no column in the list view, the only possible hook is inside <tree>
                    if (!self.columns.length) {
                        node = {
                           tag: 'tree',
                       };
                       position = 'inside';
                    }
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

        this.setSelectable(this.$('th, td').not('.o_web_studio_hook'));

        return def;
    },
    /**
     * @override
     * @private
     */
    _renderHeader: function () {
        var $header = this._super.apply(this, arguments);
        var self = this;
        // Insert a hook after each th
        _.each($header.find('th'), function (th) {
            var $new_th = $('<th>')
                .addClass('o_web_studio_hook')
                .append(
                    $('<i>').addClass('fa fa-plus')
            );
            $new_th.insertAfter($(th));
            $(th).attr('data-node-id', self.node_id++);
        });

        // Insert a hook before the first column
        var $new_th_before = $('<th>')
            .addClass('o_web_studio_hook')
            .data('position', 'before')
            .append(
                $('<i>').addClass('fa fa-plus')
        );
        $new_th_before.prependTo($header.find('tr'));
        return $header;
    },
    /**
     * @override
     * @private
     */
    _renderHeaderCell: function (node) {
        var $th = this._super.apply(this, arguments);
        if (_.contains(this.invisible_columns, node)) {
            $th.addClass('o_web_studio_show_invisible');
        }
        return $th;
    },
    /**
     * @override
     * @private
     */
    _renderEmptyRow: function () {
        // render an empty row
        var $tds = [];
         _.each(this.columns, function () {
            $tds.push($('<td>&nbsp;</td>'));
        });
        if (this.has_selectors) {
            $tds.push($('<td>&nbsp;</td>'));
        }
        var $row = $('<tr>').append($tds);

        // insert a hook after each td
        _.each($row.find('td'), function (td) {
            $('<td>')
                .addClass('o_web_studio_hook')
                .insertAfter($(td));
        });

        // insert a hook before the first column
        $('<td>')
            .addClass('o_web_studio_hook')
            .prependTo($row);

        return $row;
    },
    /**
     * @override
     * @private
     */
    _renderRow: function () {
        var $row = this._super.apply(this, arguments);

        // Inser a hook after each td
        _.each($row.find('td'), function (td) {
            $('<td>')
                .addClass('o_web_studio_hook')
                .insertAfter($(td));
        });

        // Insert a hook before the first column
        $('<td>')
            .addClass('o_web_studio_hook')
            .prependTo($row);

        return $row;
    },
    /**
     * @override
     * @private
     */
    _renderFooter: function () {
        var $footer = this._super.apply(this, arguments);

        // Insert a hook after each td
        _.each($footer.find('td'), function (td) {
            $('<td>')
                .addClass('o_web_studio_hook')
                .insertAfter($(td));
        });

        // Insert a hook before the first column
        $('<td>')
            .addClass('o_web_studio_hook')
            .prependTo($footer.find('tr'));

        return $footer;

    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onExistingColumn: function (ev) {
        var $el = $(ev.currentTarget);
        var $selected_column = $el.closest('table').find('th').eq($el.index());

        var field_name = $selected_column.data('name');
        var node = _.find(this.columns, function (column) {
            return column.attrs.name === field_name;
        });
        this.selected_node_id = $selected_column.data('node-id');
        this.trigger_up('node_clicked', {node: node});
    },
});

});
