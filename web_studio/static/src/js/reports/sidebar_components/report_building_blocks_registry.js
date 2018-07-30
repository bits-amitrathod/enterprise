odoo.define('web_studio.reportNewComponentsRegistry', function (require) {
"use strict";

var Registry = require('web.Registry');
var reportNewComponents = require('web_studio.reportNewComponents');

var registry = new Registry();

registry
    .add('address', reportNewComponents.BuildingBlockAddress)
    .add('table', reportNewComponents.BuildingBlockTable)
    .add('total', reportNewComponents.BuildingBlockTotal)
    .add('field', reportNewComponents.BuildingFieldComponent)
    .add('image', reportNewComponents.BuildingImageComponent)
    .add('title', reportNewComponents.BuildingBlockTitle)
    .add('text', reportNewComponents.BuildingTextComponent);

return registry;

});
