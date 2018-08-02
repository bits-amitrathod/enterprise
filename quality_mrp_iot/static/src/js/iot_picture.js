
odoo.define('quality_mrp_iot.iot_picture', function(require) {
"use strict";

var basic_fields = require('web.basic_fields');
var registry = require('web.field_registry');
var FieldBinaryImage = basic_fields.FieldBinaryImage;

var TabletImageIot = FieldBinaryImage.extend({
    template: 'FieldBinaryTabletImageIot',
    events: _.extend(FieldBinaryImage.prototype.events,
                     {'click .o_button_take_picture': '_onButtonClick',}), //need something for button click

    init: function() {
        this._super.apply(this, arguments);
        var ipField = this.nodeOptions.ip_field;
        this.ip = this.record.data[ipField];
        var identifierField = this.nodeOptions.identifier;
        this.identifier = this.record.data[identifierField];

    },
    _onButtonClick: function(ev) {
        var url = 'http://' + this.ip + ":8069/driveraction/camera"
        var data = {'action': 'camera', 'identifier': this.identifier}
        console.log(this)
        var self = this;
        $.ajax({type: 'POST',
                url: url,
                dataType: 'json',
                beforeSend: function(xhr){xhr.setRequestHeader('Content-Type', 'application/json');},
                data: JSON.stringify(data),
                success: function(data) {
                    self._setValue(data['result']['image']);
                    self._render();
                    console.log('success!');
                }});
    },
});


registry.add('iot_picture', TabletImageIot);

});