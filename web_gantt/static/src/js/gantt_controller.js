odoo.define('web_gantt.GanttController', function (require) {
"use strict";

var AbstractController = require('web.AbstractController');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dialogs = require('web.view_dialogs');
var time = require('web.time');

var _t = core._t;
var qweb = core.qweb;


var GanttController = AbstractController.extend({
    events: {
        'click .gantt_task_row .gantt_task_cell': 'create_on_click',
    },
    custom_events: _.extend({}, AbstractController.prototype.custom_events, {
        task_changed: 'on_task_changed',
        task_display: 'on_task_display',
        task_create: 'on_task_create',
    }),

    init: function(parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.set('title', params.title);
        this.context = params.context;
    },
    /**
     * Render the buttons according to the GanttView.buttons template and add listeners on it.
     * Set this.$buttons with the produced jQuery element
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should be inserted
     * $node may be undefined, in which case they are inserted into this.options.$buttons
     */
    renderButtons: function($node) {
        var self = this;
        if ($node) {
            this.$buttons = $(qweb.render("GanttView.buttons", {'widget': this}));
            this.$buttons.appendTo($node);
            this.$buttons.find('.o_gantt_button_scale').bind('click', function (event) {
                return self.on_scale(event.target.value);
            });
            this.$buttons.find('.o_gantt_button_left').bind('click', function () {
                var state = self.model.get();
                self.on_focus_date(state.focus_date.subtract(1, state.scale));
            });
            this.$buttons.find('.o_gantt_button_right').bind('click', function () {
                var state = self.model.get();
                self.on_focus_date(state.focus_date.add(1, state.scale));
            });
            this.$buttons.find('.o_gantt_button_today').bind('click', function () {
                self.model.setFocusDate(moment(new Date()));
                return self.reload();
            });
        }
    },

    on_focus_date: function (focus_date) {
        var self = this;
        this.model.setFocusDate(focus_date);
        this.reload().then(function () {
            self.set({'title': 'Forecast (' + self.model.get().date_display + ')'});
        });
    },

    on_task_changed: function (event) {
        var task_obj = event.data.task;
        var success = event.data.success;
        var fail = event.data.fail;
        var fields = this.model.fields;
        // TODO: modify date_delay instead of date_stop
        if (fields[this.model.mapping.date_stop] === undefined) {
            // Using a duration field instead of date_stop
            Dialog.alert(this, _t('You have no date_stop field defined!'));
            return fail();
        }
        // We first check that the fields aren't defined as readonly.
        if (fields[this.model.mapping.date_start].readonly || fields[this.model.mapping.date_stop].readonly) {
            Dialog.alert(this, _t('You are trying to write on a read-only field!'));
            return fail();
        }

        // Now we try to write the new values in the dataset. Note that it may fail
        // if the constraints defined on the model aren't met.
        var start = task_obj.start_date;
        var end = task_obj.end_date;
        var data = {};
        data[this.model.mapping.date_start] = time.auto_date_to_str(start, fields[this.model.mapping.date_start].type);
        if (this.model.mapping.date_stop) {
            data[this.model.mapping.date_stop] = time.auto_date_to_str(end, fields[this.model.mapping.date_stop].type);
        } else { // we assume date_duration is defined
            var duration = gantt.calculateDuration(start, end);
            data[this.model.mapping.date_delay] = duration;
        }
        var task_id = parseInt(task_obj.id.split("gantt_task_").slice(1)[0], 10);

        this.performModelRPC(this.model, 'write', [task_id, data]).then(success, fail);
    },

    /**
     * Dialog to edit/display a task.
     */
    on_task_display: function (event) {
        var task = event.data;
        var task_id = _.isString(task.id) ? parseInt(_.last(task.id.split("_")), 10) : task.id;

        new dialogs.FormViewDialog(this, {
            res_model: this.modelName,
            res_id: task_id,
            context: event.data,
            on_saved: this.reload.bind(this)
        }).open();
    },

    /**
     * Dialog to create a task.
     */
    on_task_create: function (event) {
        var start_date = moment(new Date()).utc();
        this._create_task(0, start_date);
    },

    on_scale: function (scale) {
        var self = this;
        this.model.setScale(scale);
        this.reload().then(function () {
            self.set({'title': 'Forecast (' + self.model.get().date_display + ')'});
        });
    },

    /**
     * Handler used when clicking on an empty cell. The behaviour is to create a new task
     * and apply some default values.
     */
    create_on_click: function (event) {
        var id = event.target.parentElement.attributes.task_id.value;
        var class_date = _.find(event.target.classList, function (e) {
            return e.indexOf("date_") > -1;
        });
        var start_date = moment(new Date(parseInt(class_date.split("_")[1], 10))).utc();

        this._create_task(id, start_date);
    },

    _create_task: function (id, start_date) {
        var task = gantt.getTask(id);

        var end_date;
        switch (this.model.get().scale) {
            case "day":
                end_date = start_date.clone().add(4, "hour");
                break;
            case "week":
                end_date = start_date.clone().add(2, "day");
                break;
            case "month":
                end_date = start_date.clone().add(4, "day");
                break;
            case "year":
                end_date = start_date.clone().add(2, "month");
                break;
        }

        var context = _.clone(this.context);
        var get_create = function (item) {
            if (item.create) {
                context["default_"+item.create[0]] = item.create[1][0];
            }
            if (item.parent) {
                var parent = gantt.getTask(item.parent);
                get_create(parent);
            }
        };
        get_create(task);

        context["default_"+this.model.mapping.date_start] = start_date.format("YYYY-MM-DD HH:mm:ss");
        if(this.model.mapping.date_stop) {
            context["default_"+this.model.mapping.date_stop] = end_date.format("YYYY-MM-DD HH:mm:ss");
        } else { // We assume date_delay is given
            context["default_"+this.model.mapping.date_delay] = gantt.calculateDuration(start_date, end_date);
        }

        context.id = 0;

        this.on_task_display({data: context});
    },
});

return GanttController;

});
