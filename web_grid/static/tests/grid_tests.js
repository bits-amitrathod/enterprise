odoo.define('web_grid.grid_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var GridView = require('web_grid.GridView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function() {
        this.data = {
            'analytic.line': {
                fields: {
                    project_id: {string: "Project", type: "many2one", relation: "project"},
                    task_id: {string: "Task", type: "many2one", relation: "task"},
                    date: {string: "Date", type: "date"},
                    unit_amount: {string: "Unit Amount", type: "float"},
                },
                records: [
                    {id: 1, project_id: 31, task_id: 1, date: "2017-01-25", unit_amount: 5.5},
                    {id: 2, project_id: 31, task_id: 1, date: "2017-01-30", unit_amount: 10},
                    {id: 4, project_id: 31, task_id: 12, date: "2017-01-31", unit_amount: 3.5},
                ]
            },
            project: {
                fields: {
                    name: {string: "Project Name", type: "char"}
                },
                records: [
                    {id: 31, display_name: "P1"},
                    {id: 142, display_name: "Webocalypse Now"}
                ]
            },
            task: {
                fields: {
                    name: {string: "Task Name", type: "char"}
                },
                records: [
                    {id: 1, display_name: "BS task"},
                    {id: 12, display_name: "Another BS task"},
                    {id: 54, display_name: "yet another task"}
                ]
            },
        };
        this.arch = '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="project_id" type="row"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                    '<empty>' +
                        '<p class="oe_view_nocontent_create">' +
                            'Click to add projects and tasks' +
                        '</p>' +
                        '<p>you will be able to register your working hours on the given task</p>' +
                    '</empty>' +
                '</grid>';
        this.archs = {
            'analytic.line,23,form': '<form string="Add a line"><group><group>' +
                                  '<field name="project_id"/>' +
                                  '<field name="task_id"/>' +
                                  '<field name="date"/>' +
                                  '<field name="unit_amount" string="Time spent"/>' +
                                '</group></group></form>',
        };
    }
}, function () {
    QUnit.module('GridView');

    QUnit.test('basic grid view', function(assert) {
        assert.expect(15);
        var done = assert.async();

        var grid = createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
            manualDestroy: true,
        });

        return concurrency.delay(0).then(function() {
            assert.ok(grid.$('table').length, "should have rendered a table");
            assert.strictEqual(grid.$('div.o_grid_cell_container').length, 7,
                "should have 7 cells");
            assert.strictEqual(grid.$('div.o_grid_input:contains(5:30)').length, 1,
                "should have correctly parsed a float_time");
            assert.strictEqual(grid.$('div.o_grid_input:contains(0:0)').length, 6,
                "should have correctly parsed another float_time");

            assert.ok(grid.$buttons.find('button.grid_arrow_previous').is(':visible'),
                "previous button should be visible");
            assert.ok(grid.$buttons.find('button.grid_arrow_range[data-name="week"]').hasClass('active'),
                "current range is shown as active");

            assert.strictEqual(grid.$('tfoot td:contains(00:00)').length, 6, "should display totals, even if 0");

            grid.$buttons.find('button.grid_arrow_next').click();
            return concurrency.delay(0);
        }).then(function() {
            assert.ok(grid.$('div.o_grid_cell_container').length, "should not have any cells");
            assert.ok(grid.$('th div:contains(P1)').length,
                "should have rendered a cell with project name");
            assert.ok(grid.$('th div:contains(BS task)').length,
                "should have rendered a cell with task name");
            assert.notOk(grid.$('.o_grid_nocontent_container p:contains(Click to add projects and tasks)').length,
                "should not have rendered a no content helper");

            assert.notOk(grid.$('td.o_grid_current').length, "should not have any cell marked current");
            grid.$buttons.find('button.grid_arrow_next').click();

            return concurrency.delay(0);
        }).then(function() {
            assert.ok(grid.$('.o_grid_nocontent_container p:contains(Click to add projects and tasks)').length,
                "should have rendered a no content helper");

            assert.notOk(grid.$('div.o_grid_cell_container').length, "should not have any cell");

            var emptyTd = 0;
            grid.$('tfoot td').each(function() {
                if ($(this).text() === '') {
                    emptyTd++;
                }
            });
            assert.strictEqual(emptyTd, 8, "8 totals cells should be empty");
            grid.destroy();
            done();
        });

    });

    QUnit.test('create analytic lines', function(assert) {
        assert.expect(7);
        var done = assert.async();
        this.data['analytic.line'].fields.date.default = "2017-02-25";

        var grid = createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="project_id" type="row"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            currentDate: "2017-02-25",
            manualDestroy: true,
            viewOptions: {
                views: [[23, 'form']],
            },
            archs: this.archs,
            mockRPC: function(route, args) {
                if (args.method === 'create') {
                    assert.strictEqual(args.args[0].date, "2017-02-25",
                        "default date should be current day");
                }
                return this._super(route, args);
            },
        });

        return concurrency.delay(0).then(function() {
            assert.strictEqual(grid.$('.o_grid_nocontent_container').length, 0,
                "should not have rendered a no content helper");

            assert.strictEqual(grid.$('div.o_grid_cell_container').length, 0, "should not have any cells");
            assert.notOk($('div.modal').length, "should not have any modal open");
            grid.$('.o_grid_button_add').click();

            assert.ok($('div.modal').length, "should have opened a modal");

            // input a project and a task
            for (var i = 0; i< 2; i++) {
                $('.modal .o_form_field_many2one input').eq(i).click();
                $('.modal .o_form_field_many2one input').eq(i).autocomplete('widget').find('a').first().click();
            }

            // input unit_amount
            $('.modal input').eq(3).val("4").trigger('input');

            // save
            $('.modal .modal-footer button.btn-primary').click();
            return concurrency.delay(0);
        }).then(function() {
            assert.strictEqual(grid.$('div.o_grid_cell_container').length, 7,
                "should have 7 cell containers (1 for each day)");

            assert.strictEqual(grid.$('td.o_grid_total:contains(4:00)').length, 1,
                "should have a total of 4:00");

            grid.destroy();
            done();
        });

    });

    QUnit.test('switching active range', function(assert) {
        assert.expect(6);
        var done = assert.async();
        this.data['analytic.line'].fields.date.default = "2017-02-25";

        var grid = createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="project_id" type="row"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            currentDate: "2017-02-25",
            manualDestroy: true,
        });

        return concurrency.delay(0).then(function() {
            assert.strictEqual(grid.$('thead th:not(.o_grid_title_header)').length, 8,
                "should have 8 columns (1 for each day + 1 for total)");
            assert.ok(grid.$buttons.find('button.grid_arrow_range[data-name="week"]').hasClass('active'),
                "current range is shown as active");
            assert.notOk(grid.$buttons.find('button.grid_arrow_range[data-name="month"]').hasClass('active'),
                "month range is not active");

            grid.$buttons.find('button[data-name=month]').click();

            return concurrency.delay(0);
        }).then(function() {

            assert.strictEqual(grid.$('thead th:not(.o_grid_title_header)').length, 29,
                "should have 29 columns (1 for each day + 1 for total)");
            assert.ok(grid.$buttons.find('button.grid_arrow_range[data-name="month"]').hasClass('active'),
                "month range is shown as active");
            assert.notOk(grid.$buttons.find('button.grid_arrow_range[data-name="week"]').hasClass('active'),
                "week range is not active");

            grid.destroy();
            done();
        });

    });

    QUnit.test('clicking on the info icon on a cell triggers a do_action', function(assert) {
        assert.expect(3);
        var done = assert.async();

        var grid = createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
            manualDestroy: true,
        });

        return concurrency.delay(0).then(function() {
            assert.strictEqual(grid.$('i.o_grid_cell_information').length, 7,
                "should have 7 icons to open cell info");

            testUtils.intercept(grid, 'do_action', function(event) {
                var action = event.data.action;

                assert.deepEqual(action.domain, [], "should trigger a do_action with correct values");
                assert.strictEqual(action.name, "P1: BS task",
                    "should have correct action name");
            });
            grid.$('i.o_grid_cell_information').eq(2).click();

            grid.destroy();
            done();
        });
    });
});
});