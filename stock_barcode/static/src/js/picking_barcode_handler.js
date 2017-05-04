odoo.define('stock_barcode.PickingBarcodeHandler', function (require) {
"use strict";

var core = require('web.core');
var AbstractField = require('web.AbstractField');
var field_registry = require('web.field_registry');
var FormController = require('web.FormController');

var _t = core._t;

FormController.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Used to find the product who match with the scanned barcode
     *
     * @private
     * @override
     * @param {Object} record
     * @param {string} barcode
     * @param {Object} activeBarcode
     * @returns {Deferred}
     */
    _barcodeRecordFilter: function (record, barcode, activeBarcode) {
        if (activeBarcode.widget === 'picking_barcode_handler') {
            return record.data.product_barcode === barcode &&
                !record.data.lots_visible &&
                !record.data.location_processed &&
                !record.data.result_package_id &&
                record.data.qty_done < record.data.product_qty;
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Method called when a record is already found
     *
     * @private
     * @override
     * @param {Object} candidate (already exists in the x2m)
     * @param {Object} record
     * @param {string} barcode
     * @param {Object} activeBarcode
     * @returns {Deferred}
     */
    _barcodeSelectedCandidate: function (candidate, record, barcode, activeBarcode) {
        if (activeBarcode.widget === 'picking_barcode_handler') {
            var self = this;
            return this.saveRecord().done(function() {
                return self._rpc({
                        model: 'stock.picking',
                        method: 'get_po_to_split_from_barcode',
                        args: [[record.data.id], barcode],
                    })
                    .then(function (id) {
                        return self._rpc({
                                model: 'stock.pack.operation',
                                method: 'action_split_lots',
                                args: [[id]],
                            });
                    }).done(function (action) {
                        self.trigger('detached');
                        self.do_action(action, {
                            on_close: function() {
                                self.trigger('attached');
                                self.update({}, {reload: true});
                            }
                        });
                    });
            });
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Method called when no records match
     *
     * @private
     * @override
     * @param {Object} record
     * @param {string} barcode
     * @param {Object} activeBarcode
     * @returns {Deferred}
     */
    _barcodeWithoutCandidate: function (record, barcode, activeBarcode) {
        if (activeBarcode.widget === 'picking_barcode_handler') {
            this.do_warn(_t("Can't find the product for this Picking"));
            return $.when();
        }
        return this._super.apply(this, arguments);
    },
    /**
     *
     * @see _barcodeAddX2MQuantity
     *
     * @private
     * @param {string} barcode
     * @param {Object} activeBarcode
     * @returns {Deferred}
     */
    _barcodePickingAddRecordId: function (barcode, activeBarcode) {
        if (!activeBarcode.handle) {
            return $.Deferred().reject();
        }
        var record = this.model.get(activeBarcode.handle);
        if (record.data.state === 'cancel' || record.data.state === 'done') {
            this.do_warn(_.str.sprintf(_t("Picking %s"), record.data.state),
                _.str.sprintf(_t("The picking is %s and cannot be edited."), record.data.state));
            return $.Deferred().reject();
        }
        return this._barcodeAddX2MQuantity(barcode, activeBarcode);
    }
});


var PickingBarcodeHandler = AbstractField.extend({
    init: function() {
        this._super.apply(this, arguments);

        this.trigger_up('activeBarcode', {
            name: this.name,
            fieldName: 'pack_operation_product_ids',
            quantity: 'qty_done',
            commands: {
                'barcode': '_barcodePickingAddRecordId',
                'O-CMD.MAIN-MENU': _.bind(this.do_action, this, 'stock_barcode.stock_barcode_action_main_menu', {clear_breadcrumbs: true}),
            }
        });
    },
});

field_registry.add('picking_barcode_handler', PickingBarcodeHandler);

return PickingBarcodeHandler;

});
