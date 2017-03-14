odoo.define('web_enterprise.upgrade_fields_tests', function (require) {
"use strict";

/**
 * Upgrade widgets have a specific behavior in community which is overriden
 * in enterprise by the default FieldBoolean and FieldRadio behaviors
 */

var basic_fields = require('web.basic_fields');
var field_registry = require('web.field_registry');
var relational_fields = require('web.relational_fields');

QUnit.module('fields', {}, function () {

    QUnit.module('FieldUpgrade');

    QUnit.test('upgrade widgets in registry', function (assert) {
        assert.expect(4);

        assert.ok(basic_fields.FieldBoolean, "FieldBoolean should exist");
        assert.ok(relational_fields.FieldRadio, "FieldRadio should exist");
        assert.strictEqual(field_registry.get('upgrade_boolean'), basic_fields.FieldBoolean,
            "The 'upgrade_boolean' widget should be FieldBoolean in enterprise");
        assert.strictEqual(field_registry.get('upgrade_radio'), relational_fields.FieldRadio,
            "The 'upgrade_radio' widget should be FieldRadio in enterprise");
    });

});

});
