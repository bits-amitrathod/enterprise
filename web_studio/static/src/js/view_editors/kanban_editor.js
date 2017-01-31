odoo.define('web_studio.KanbanEditor', function (require) {
"use strict";

var core = require('web.core');
var KanbanRecordEditor = require('web_studio.KanbanRecordEditor');
var KanbanRenderer = require('web.KanbanRenderer');

var _t = core._t;

return KanbanRenderer.extend({
    className: KanbanRenderer.prototype.className + ' o_web_studio_kanban_view_editor',
    init: function(parent) {
        this._super.apply(this, arguments);

        // only render one record
        this.state.data = this.state.data.slice(0, 1);
        this.all_fields = parent.fields;
    },
    _render: function () {
        if (this.state.data.length === 0) {
            return this._render_empty_editor();
        }

        var is_grouped = !!this.arch.attrs.default_group_by;
        this.$el.toggleClass('o_kanban_grouped', is_grouped);
        this.$el.toggleClass('o_kanban_ungrouped', !is_grouped);

        this.$el.empty();
        var fragment = document.createDocumentFragment();
        this._render_ungrouped(fragment);

        if (is_grouped) {
            var $group = $('<div>', {class: 'o_kanban_group'});
            $group.append(fragment);
            this.$el.append($group);

            // render a second empty column
            var fragment_empty = document.createDocumentFragment();
            this._render_demo_divs(fragment_empty, 7);
            this._render_ghost_divs(fragment_empty);
            var $group_empty = $('<div>', {class: 'o_kanban_group'});
            $group_empty.append(fragment_empty);
            this.$el.append($group_empty);
        } else {
            this.$el.append(fragment);
        }
        return $.when();
    },
    _render_empty_editor: function() {
        var style = {
            color: 'white',
            fontSize: '24px',
        };
        var $message = $('<div>').css(style).text(_t('No records to display'));
        this.$el.html($message);
        return $.when();
    },
    _render_ungrouped: function(fragment) {
        // overwrite this method to use the KanbanRecordEditor
        var self = this;
        _.each(this.state.data, function (record) {
            var is_dashboard = self.$el.hasClass('o_kanban_dashboard');
            self.kanban_record = new KanbanRecordEditor(self, record, self.record_options, self.all_fields, is_dashboard);
            self.widgets.push(self.kanban_record);
            self.kanban_record.appendTo(fragment);
        });
        this._render_demo_divs(fragment, 6);
        this._render_ghost_divs(fragment);
    },
    _render_demo_divs: function (fragment, nb_divs) {
        for (var i = 0, demo_div; i < nb_divs; i++) {
            demo_div = $("<div>").addClass("o_kanban_record o_kanban_demo");
            demo_div.appendTo(fragment);
        }
    },
    highlight_nearest_hook: function(pageX, pageY) {
        if (this.kanban_record) {
            return this.kanban_record.highlight_nearest_hook(pageX, pageY);
        }
    },
    get_local_state: function() {
        var state = this._super.apply(this, arguments);
        if (this.kanban_record && this.kanban_record.selected_node_id) {
            state.selected_node_id = this.kanban_record.selected_node_id;
        }
        return state;
    },
    set_local_state: function(state) {
        if (this.kanban_record) {
            this.kanban_record.set_local_state(state);
        }
    },
});

});
