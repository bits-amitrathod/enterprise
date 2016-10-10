odoo.define('web.gantt_tests', function (require) {
"use strict";

var GanttView = require('web_gantt.GanttView');
var testUtils = require('web.test_utils');

var initialDate = new Date("2016-12-12 08:00:00");

var createAsyncView = testUtils.createAsyncView;

QUnit.module('Views', {
    beforeEach: function() {
        this.data = {
            task: {
                fields: {
                    id: {string: "ID", type: "int"},
                    name: {string: "name", type: "char"},
                    start: {string: "start", type: "datetime"},
                    stop: {string: "stop", type: "datetime"},
                    progress: {string: "progress", type: "int"},
                },
                records: [
                    {id: 1, name: "task 1", start: "2016-12-11 00:00:00", stop: "2016-12-11 00:00:00", progress: 50},
                    {id: 2, name: "task 2", start: "2016-12-12 10:55:05", stop: "2016-12-12 14:55:05", progress: 30},
                    {id: 3, name: "task 3", start: "2016-12-12 15:55:05", stop: "2016-12-12 16:55:05", progress: 20},
                    {id: 4, name: "task 4", start: "2016-12-14 15:55:05", stop: "2016-12-14 18:55:05", progress: 90},
                    {id: 5, name: "task 5", start: "2016-12-23 15:55:05", stop: "2016-12-26 18:55:05", progress: 10},
                    {id: 6, name: "task 6", start: "2016-12-28 08:00:00", stop: "2016-12-28 09:00:00", progress: 30},
                ]
            },
        };
    }
}, function () {
    QUnit.module('GanttView');

    QUnit.test('simple gantt view', function(assert) {
        assert.expect(9);
        var done = assert.async();

        createAsyncView({
            View: GanttView,
            model: 'task',
            data: this.data,
            arch: '<gantt date_start="start" date_stop="stop" progress="progress"></gantt>',
            viewOptions: {
                initialDate: initialDate,
                action: {name: "Forecasts"}
            },
        }).then(function(gantt) {
            assert.strictEqual(gantt.get('title'), "Forecasts", "should have correct title");
            assert.ok(gantt.$('.gantt_task_scale').length, "should gantt scale part");
            assert.ok(gantt.$('.gantt_data_area').length, "should gantt data part");
            assert.ok(gantt.$('.gantt_hor_scroll').length, "should gantt horizontal scroll bar");
            assert.strictEqual(gantt.$('.gantt_bars_area .gantt_task_line').length, 6,
                "should display 6 tasks");

            gantt.$buttons.find('.o_gantt_button_scale[value="day"]').trigger('click');
            assert.strictEqual(gantt.$('.gantt_bars_area .gantt_task_line').length, 4,
                "should display 4 tasks in day mode");
            assert.strictEqual(gantt.get('title'), "Forecast (12 Dec)", "should have correct title");

            gantt.$buttons.find('.o_gantt_button_right').trigger('click');
            assert.strictEqual(gantt.$('.gantt_bars_area .gantt_task_line').length, 3,
                "should now display 3 tasks");

            gantt.$buttons.find('.o_gantt_button_left').trigger('click');
            assert.strictEqual(gantt.$('.gantt_bars_area .gantt_task_line').length, 4,
                "should now display 4 tasks");

            done();
        });
    });

    QUnit.test('create a task', function(assert) {
        assert.expect(5);
        var done = assert.async();

        var self = this;

        var rpcCount = 0;

        createAsyncView({
            View: GanttView,
            model: 'task',
            data: this.data,
            arch: '<gantt date_start="start" date_stop="stop" progress="progress"></gantt>',

            archs: {
                'task,false,form': '<form string="Task">' +
                                    '<field name="name"/>' +
                                    '<field name="start"/>' +
                                    '<field name="stop"/>' +
                                    '</form>',
            },
            viewOptions: {
                initialDate: new Date("4567-4-4 08:00:00"),
                action: {name: "Forecasts"}
            },
            mockRPC: function(route, args) {
                rpcCount++;
                return this._super(route, args);
            },
        }).then(function(gantt) {

            // when no tasks are present, the gantt library will add an empty
            // task line
            assert.strictEqual(gantt.$('.gantt_bars_area .gantt_task_line').length, 1,
                "should display 1 tasks line");

            gantt.$('.gantt_task_cell').first().click();
            $('.modal .modal-body input:first').val('new task').trigger('input');

            rpcCount = 0;
            $('.modal .modal-footer button.btn-primary').click();  // save

            assert.strictEqual(rpcCount, 2, "should have done 2 rpcs (1 write and 1 searchread to reload)");

            assert.notOk($('.modal').length, "should have closed the modal");
            assert.ok($('div.gantt_tree_content:contains(new task)').length,
                "should display the task name in the dom");

            assert.strictEqual(self.data.task.records.length, 7, "should have created a task");
            done();
        });
    });
});
});