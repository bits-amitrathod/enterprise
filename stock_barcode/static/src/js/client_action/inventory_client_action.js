odoo.define('stock_barcode.inventory_client_action', function (require) {
'use strict';

var core = require('web.core');
var ClientAction = require('stock_barcode.ClientAction');
var ViewsWidget = require('stock_barcode.ViewsWidget');

var _t = core._t;

var InventoryClientAction = ClientAction.extend({
    custom_events: _.extend({}, ClientAction.prototype.custom_events, {
        validate: '_onValidate',
        cancel: '_onCancel',
        show_information: '_onShowInformation',
        picking_print_inventory: '_onPrintInventory'
    }),

    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.mode = 'inventory';
        if (! this.actionParams.inventoryId) {
            this.actionParams.inventoryId = action.context.active_id;
            this.actionParams.model = 'stock.inventory';
        }
    },

    willStart: function () {
        var self = this;
        var res = this._super.apply(this, arguments);
        res.then(function () {
            if (self.currentState.group_stock_multi_locations === false) {
                self.mode = 'no_multi_locations';
            } else  {
                self.mode = 'inventory';
            }
            if (self.currentState.state === 'done') {
                self.mode = 'done';
            }
        });
        return res;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getWriteableFields: function () {
        return ['product_qty', 'location_id.id', 'prod_lot_id.id'];
    },


    /**
     * @override
     */
     _getPageFields: function () {
         return [
             ['location_id', 'location_id.id'],
             ['location_name', 'location_id.display_name'],
         ];
     },

    /**
     * @override
     */
    _getLines: function (state) {
        return state.line_ids;
    },


    /**
     * @override
     */
    _makeNewLine: function (product, barcode, qty_done) {
        var virtualId = this._getNewVirtualId();
        var currentPage = this.pages[this.currentPageIndex];
        var newLine = {
            'inventory_id': this.currentState.id,
            'product_id': {
                'id': product.id,
                'display_name': product.display_name,
                'barcode': barcode
            },
            'product_barcode': barcode,
            'display_name': product.display_name,
            'product_qty': qty_done,
            'theoretical_qty': 0,
            'product_uom_id': product.uom_id[0],
            'location_id': {
                'id': currentPage.location_id,
                'name': currentPage.location_name,
            },
            'state': 'confirm',
            'reference': this.name,
            'virtual_id': virtualId,
        };
        return newLine;
    },

    /**
     * @override
     */
    _applyChanges: function (changes) {
        var formattedCommands = [];
        var cmd = [];
        for (var i in changes) {
            var line = changes[i];

            // Lines needs to be updated
            if (line.id) {
                cmd = [1, line.id, {
                    'product_qty' : line.product_qty,
                    'prod_lot_id': line.prod_lot_id && line.prod_lot_id[0]
                }];
                formattedCommands.push(cmd);
            // Lines needs to be created
            } else {
                cmd = [0, 0, {
                    // TODO : Add prod_lot_id and package_id
                    'product_id':  line.product_id.id,
                    'product_uom_id': line.product_uom_id,
                    'product_qty': line.product_qty,
                    'location_id': line.location_id.id,
                    'prod_lot_id': line.prod_lot_id && line.prod_lot_id[0]
                }];
                formattedCommands.push(cmd);
            }
        }
        var self = this;
        var deferred = $.when();
        if (formattedCommands.length > 0){
            deferred = this._rpc({
                'model': this.actionParams.model,
                'method': 'write',
                'args': [[this.currentState.id], {
                    'line_ids': formattedCommands,
                }],
            }).then( function () {
                return self._getState(self.currentState.id);
            });
        }
        return deferred;
    },

    /**
     * @override
     */
    _showInformation: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            if (self.ViewsWidget) {
                self.ViewsWidget.destroy();
            }
            self.linesWidget.destroy();
            self.ViewsWidget = new ViewsWidget(
                self,
                'stock.inventory',
                'stock_barcode.stock_inventory_barcode2',
                {},
                {currentId :self.currentState.id},
                'readonly'
            );
            self.ViewsWidget.appendTo(self.$el);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles the `validate` OdooEvent.
     *
     * @private
     * @param {OdooEvent} ev
     */
     _onValidate: function (ev) {
        ev.stopPropagation();
        var self = this;
        return this.mutex.exec(function () {
            return self._save().then(function () {
                self._rpc({
                    'model': self.actionParams.model,
                    'method': 'action_validate',
                    'args': [[self.currentState.id]],
                }).then(function () {
                    self.do_notify(_t("Success"), _t("The inventory adjustment has been validated"));
                    return self.trigger_up('exit');
                });
            });
        });
    },

    /**
    * Handles the `cancel` OdooEvent.
    *
    * @private
    * @param {OdooEvent} ev
    */
    _onCancel: function (ev) {
        ev.stopPropagation();
        var self = this;
        this.mutex.exec(function () {
            return self._save().then(function () {
                return self._rpc({
                    'model': self.actionParams.model,
                    'method': 'action_cancel_draft',
                    'args': [[self.currentState.id]],
                }).then(function () {
                    self.do_notify(_t("Cancel"), _t("The inventory adjustment has been cancelled"));
                    self.trigger_up('exit');
                });
            });
        });
    },

    /**
     * Handles the `print_inventory` OdooEvent. It makes an RPC call
     * to the method 'do_action' on a 'ir.action_window' with the additional context
     * needed
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onPrintInventory: function (ev) {
        ev.stopPropagation();
        var self = this;
        this.mutex.exec(function () {
            return self._save().then(function () {
                return self.do_action(self.currentState.actionReportInventory, {
                    'additional_context': {
                        'active_id': self.actionParams.id,
                        'active_ids': [self.actionParams.inventoryId],
                        'active_model': 'stock.inventory',
                    }
                });
            });
        });
    },

});

core.action_registry.add('stock_barcode_inventory_client_action', InventoryClientAction);

return InventoryClientAction;

});
