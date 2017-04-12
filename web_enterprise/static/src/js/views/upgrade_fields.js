odoo.define('web_enterprise.upgrade_widgets', function (require) {
"use strict";

/**
 * This module adds two field widgets in the view registry: 'upgrade_boolean'
 * and 'upgrade_radio'. In community, those widgets implement a specific
 * behavior to upgrade to enterprise. This behavior is overriden in enterprise
 * by the default FieldBoolean and FieldRadio behaviors.
 */

var basic_fields = require('web.basic_fields');
var field_registry = require('web.field_registry');
var relational_fields = require('web.relational_fields');

field_registry
    .add('upgrade_boolean', basic_fields.FieldBoolean)
    .add('upgrade_radio', relational_fields.FieldRadio);

});
