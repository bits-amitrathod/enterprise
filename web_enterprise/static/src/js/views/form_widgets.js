odoo.define('web_enterprise.form_widgets', function (require) {
"use strict";

var basic_fields = require('web.basic_fields');
var field_registry = require('web.field_registry');

field_registry
    .add('upgrade_boolean', basic_fields.FieldBoolean) // community compatibility
    .add('upgrade_radio', basic_fields.FieldRadio); // community compatibility

});