odoo.define('mrp_barcode.MrpBarcodeHandler', function (require) {
"use strict";

var fieldRegistry = require('web.field_registry');
var field = require('barcodes.field');


// var WorkorderBarcodeHandler = field.FormViewBarcodeHandler.extend({

//     init: function() {
//         if (parent.ViewManager.action) {
//             this.form_view_initial_mode = parent.ViewManager.action.context.form_view_initial_mode;
//         } else if (parent.ViewManager.view_form) {
//             this.form_view_initial_mode = parent.ViewManager.view_form.options.initial_mode;
//         }
//         console.log(arguments);
//         return this._super.apply(this, arguments);
//     },
//     start: function() {
//         this._super();
//         this.form_view.options.disable_autofocus = 'true';
//         if (this.form_view_initial_mode) {
//             this.form_view.options.initial_mode = this.form_view_initial_mode;
//         }
//     },
// });


fieldRegistry.add('workorder_barcode_handler', field.FormViewBarcodeHandler);

});
