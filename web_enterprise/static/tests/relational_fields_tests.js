odoo.define('web_enterprise.relational_fields_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('web_enterprise', {}, function () {

QUnit.module('relational_fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    trululu: 4,
                }, {
                    id: 2,
                    display_name: "second record",
                    trululu: 1,
                }, {
                    id: 4,
                    display_name: "aaa",
                }],
            },
        };
    }
}, function () {

    QUnit.module('FieldStatus');

    QUnit.test('statusbar is rendered correclty on small devices', function (assert) {
        assert.expect(6);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar"/></header>' +
                    '<field name="display_name"/>' +
                '</form>',
            res_id: 1,
            config: {
                isMobile: true,
            },
        });

        assert.strictEqual(form.$('.o_statusbar_status > button:contains(aaa)').length, 1,
            "should have only one visible status in mobile, the active one");
        assert.strictEqual(form.$('.o_statusbar_status .o-status-more').length, 1,
            "should have a dropdown containing all status");
        assert.strictEqual(form.$('.o_statusbar_status .o-status-more:visible').length, 0,
            "dropdown should be hidden");

        // open the dropdown
        form.$('.o_statusbar_status > button').click();
        assert.strictEqual(form.$('.o_statusbar_status .o-status-more:visible').length, 1,
            "dropdown should be visible");
        assert.strictEqual(form.$('.o_statusbar_status .o-status-more li').length, 3,
            "should have 3 status");
        var $activeStatus = form.$('.o_statusbar_status .o-status-more li button[data-value=4]');
        assert.ok($activeStatus.hasClass('btn-primary'), "active status should be btn-primary");

        form.destroy();
    });
});
});
});
