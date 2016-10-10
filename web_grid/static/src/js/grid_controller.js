odoo.define('web_grid.GridController', function (require) {
"use strict";

var AbstractController = require('web.AbstractController');
var dialogs = require('web.view_dialogs');
var utils = require('web.utils');
var Widget = require('web.Widget');


var GridController = AbstractController.extend({
    events: {
        "click .o_grid_button_add": "_onAddLine",
        'click .o_grid_cell_information': "_onClickCellInformation",
    },
    custom_events: _.extend({}, AbstractController.prototype.custom_events, {
        update: "_onUpdate",
    }),

    // inherited methods
    init: function(parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.set('title', params.title);
        this.context = params.context;
        this.navigationButtons = params.navigationButtons;
        this.ranges = params.ranges;
        this.formViewID = params.formViewID;
        this.listViewID = params.listViewID;
    },
    renderButtons: function ($node) {
        var first_range = this.ranges[0];
        // var range_name =
        //     this.getParent()._model.context().eval()['grid_range']
        //     || first_range && first_range.name;

        var state = this.model.get();
        this._navigation = new Arrows(this, this.navigationButtons, this.ranges, first_range, state.prev, state.next);
        this._navigation.appendTo($node);
        this.$buttons = this._navigation.$el;
    },
    update: function() {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var state = self.model.get();
            self._navigation.update(state.prev, state.next, state.range);
        });
    },

    // event handlers
    _onAddLine: function(event) {
        var self = this;
        event.preventDefault();

        // TODO: document quick_create_view (?) context key
        // var ctx = pyeval.eval('context', self._model.context());
        // context: form_context,
        // var form_context = this.get_full_context({'view_grid_add_line': true});
        // var formDescription = self.ViewManager.views.form;
        // var formViewID = ctx['quick_create_view'] || this.formViewID || false;
        var formViewID = this.formViewID || false;
        new dialogs.FormViewDialog(this, {
            res_model: self.modelName,
            res_id: false,
            view_id: formViewID,
            title: self.add_label,
            disable_multiple_selection: true,
            on_saved: this.reload.bind(this),
        }).open();
    },
    _onClickCellInformation: function (e) {
        var $target = $(e.target);
        var cell_path = $target.parent().attr('data-path').split('.');
        var row_path = cell_path.slice(0, -3).concat(['rows'], cell_path.slice(-2, -1));
        var state = this.model.get();
        var cell = utils.into(state, cell_path);
        var row = utils.into(state, row_path);

        var label = _.map(state.groupBy, function(g) {
            return row.values[g][1];
        }).join(': ');

        this.do_action({
            type: 'ir.actions.act_window',
            name: label,
            res_model: this.modelName,
            views: [
                [this.listViewID, 'list'],
                [this.formViewID, 'form']
            ],
            domain: cell.domain,
            context: state.context,
        });
    },
    _onUpdate: function(event) {
        var props = {};
        props[event.data.key] = event.data.value;
        this.update(props);
    },
});

var Arrows = Widget.extend({
    template: 'grid.GridArrows',
    events: {
        'click .grid_arrow_previous': "_onArrowPrevious",
        'click .grid_arrow_next': "_onArrowNext",
        'click .grid_arrow_range': "_onRangeChange",
        'click .grid_arrow_button': "_onButtonClicked",
    },
    // inherited methods
    init: function (parent, buttons, ranges, currentRange, prev, next) {
        this._super.apply(this, arguments);
        this._ranges = ranges;
        this._buttons = buttons;
        this.currentRange = currentRange.name;
        this.prev = prev;
        this.next = next;
    },
    start: function () {
        this.update(this.prev, this.next, this.currentRange);
    },
    update: function(prev, next, range) {
        this.prev = prev;
        this.next = next;

        this.$('.grid_arrow_previous').toggleClass('hidden', !prev);
        this.$('.grid_arrow_next').toggleClass('hidden', !next);
        this.$('.grid_arrow_range[data-name=' + range + ']')
                .addClass('active')
                .siblings().removeClass('active');
    },

    // event handlers
    _onArrowPrevious: function (e) {
        e.stopPropagation();
        this.trigger_up('update', {key: 'pagination', value: this.prev});
    },
    _onArrowNext: function (e) {
        e.stopPropagation();
        this.trigger_up('update', {key: 'pagination', value: this.next});
    },
    _onRangeChange: function (e) {
        e.stopPropagation();
        var $target = $(e.target);
        if ($target.hasClass('active')) {
            return;
        }
        this.trigger_up('update', {key: 'range', value: $target.attr('data-name')});
    },
    _onButtonClicked: function (e) {
        e.stopPropagation();
        // TODO: maybe allow opting out of getting ids?
        // var button = this._buttons[$(e.target).attr('data-index')];
        // var parent = this.getParent();
        // var context = parent.get_full_context(button.context);
        // parent.get_ids().then(function (ids) {
        //     this.trigger_up('execute_action', {
        //         action_data: button,
        //         dataset: new data.DataSetStatic(this, parent._model.name, context, ids),
        //         on_close: parent.proxy('_fetch'),
        //     });
        // }.bind(this));
    },
});

return GridController;

});
