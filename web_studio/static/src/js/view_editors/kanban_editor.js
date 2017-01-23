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
        } else {
            this.$el.append(fragment);
        }
        this.$('.o_kanban_ghost').toggleClass('o_kanban_ghost').toggleClass('o_kanban_demo');
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
        this._render_ghost_divs(fragment);
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
