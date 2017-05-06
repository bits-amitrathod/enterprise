odoo.define('website_calendar.tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var session = require('web.session');

var createView = testUtils.createView;

QUnit.module('website_calendar', {
    beforeEach: function () {
        this.data = {
            'calendar.appointment.type': {
                fields: {
                    name: {type: 'char'},
                    website_url: {type: 'char'},
                    employee_ids: {type: 'many2many', relation: 'hr.employee'},
                },
                records: [{
                    id: 1,
                    name: 'Very Interdesting Meeting',
                    website_url: '/website/calendar/schedule-a-demo-1/appointment',
                    employee_ids: [214],
                }],
            },
            'hr.employee': {
                fields: {
                    id: {type: 'integer'},
                    name: {type: 'char'},
                },
                records: [{
                    id: 214,
                    name: 'Denis Ledur',
                }],
            },
        };
    },
}, function () {

    QUnit.test("empty previous_order widget", function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            arch: '<form>' +
                    '<field name="website_url" invisible="1"/>' +
                    '<sheet>' +
                        '<field name="employee_ids">' +
                            '<tree string="Employees">' +
                                '<field name="name"/>' +
                                '<field name="id" widget="appointment_employee_url" string="Individual Appointment Link" context="{\'url\': parent.website_url}" readonly="1"/>' +
                            '</tree>' +
                            '<form string="Employees">' +
                                '<group>' +
                                    '<field name="name" class="avoid_me"/>' +
                                '</group>' +
                            '</form>' +
                        '</field>' +
                    '</sheet>' +
                  '</form>',
            data: this.data,
            res_id: 1,
            model: 'calendar.appointment.type',
        });

        var actual = form.$('.o_form_uri').attr('href');
        var expected = session['web.base.url'] + '/website/calendar/schedule-a-demo-1?employee_id=214';
        assert.strictEqual(actual, expected, actual + ' != ' + expected);

        form.$('.o_website_calendar_copy_icon').click();
        // ensure we didn't open the form view
        assert.ok($('.avoid_me').length === 0);

        form.destroy();
    });
});
});
