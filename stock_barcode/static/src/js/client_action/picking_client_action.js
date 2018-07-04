odoo.define('stock_barcode.picking_client_action', function (require) {
'use strict';

var core = require('web.core');
var ClientAction = require('stock_barcode.ClientAction');
var FormWidget = require('stock_barcode.FormWidget');

var PickingClientAction = ClientAction.extend({
    custom_events: _.extend({}, ClientAction.prototype.custom_events, {
        'picking_print_delivery_slip': '_onPrintDeliverySlip',
        'picking_print_picking': '_onPrintPicking',
        'picking_scrap': '_onScrap',
        'validate': '_onValidate',
        'cancel': '_onCancel',
    }),

    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.commands['O-BTN.scrap'] = this._scrap.bind(this);
        this.commands['O-BTN.validate'] = this._validate.bind(this);
        this.commands['O-BTN.cancel'] = this._cancel.bind(this);
        if (! this.actionParams.pickingId) {
            this.actionParams.pickingId = action.context.active_id;
            this.actionParams.model = 'stock.picking';
        }
    },

    willStart: function () {
        var self = this;
        var res = this._super.apply(this, arguments);
        res.then(function() {
            // Get the usage of the picking type of `this.picking_id` to chose the mode between
            // `receipt`, `internal`, `delivery`.
            var picking_type_code = self.currentState.picking_type_code;
            if (picking_type_code === 'incoming') {
                self.mode = 'receipt';
            } else if (picking_type_code === 'outgoing') {
                self.mode = 'delivery';
            } else {
                self.mode = 'internal';
            }

            if (self.currentState.group_stock_multi_locations === false) {
                self.mode = 'no_multi_locations';
            }

            if (self.currentState.state === 'done') {
                self.mode = 'done';
            } else if (self.currentState.state === 'cancel') {
                self.mode = 'cancel';
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
    _getLines: function (state) {
        return state.move_line_ids;
    },

    /**
     * @override
     */
    _getPageFields: function () {
        return [
            ['location_id', 'location_id.id'],
            ['location_name', 'location_id.display_name'],
            ['location_dest_id', 'location_dest_id.id'],
            ['location_dest_name', 'location_dest_id.display_name'],
        ];
    },

    /**
     * @override
     */
    _getWriteableFields: function () {
        return ['qty_done', 'location_id.id', 'location_dest_id.id', 'lot_name', 'lot_id.id'];
    },

    /**
     * @override
     */
    _makeNewLine: function (product, barcode, qty_done) {
        var virtualId = this._getNewVirtualId();
        var currentPage = this.pages[this.currentPageIndex];
        var newLine = {
            'picking_id': this.currentState.id,
            'product_id': {
                'id': product.id,
                'display_name': product.display_name,
                'barcode': barcode,
                'tracking': product.tracking,
            },
            'product_barcode': barcode,
            'display_name': product.display_name,
            'product_uom_qty': 0,
            'product_uom_id': product.uom_id,
            'qty_done': qty_done,
            'location_id': {
                'id': currentPage.location_id,
                'display_name': currentPage.location_name,
            },
            'location_dest_id': {
                'id': currentPage.location_dest_id,
                'display_name': currentPage.location_dest_name,
            },
            'state': 'assigned',
            'reference': this.name,
            'virtual_id': virtualId,
        };
        return newLine;
    },

    /**
     * Makes the rpc to `button_validate`.
     *
     * @private
     * @returns {Deferred}
     */
    _validate: function () {
        var self = this;
        return self._save().then(function () {
            return self._rpc({
                'model': self.actionParams.model,
                'method': 'button_validate',
                'args': [[self.actionParams.pickingId]],
            }).then(function (res) {
                var def = $.when();
                var exitCallback = function () { self.trigger_up('exit');};
                if (res) {
                    var options = {
                        on_close: exitCallback,
                    };
                    def.then(function () {
                        return self.do_action(res, options);
                    });
                } else {
                    return def.then(function () {
                        return exitCallback();
                    });
                }
            });
        });
    },

    /**
     * Makes the rpc to `action_cancel`.
     *
     * @private
     */
    _cancel: function () {
        var self = this;
        return self._save().then(function () {
            return self._rpc({
                'model': self.actionParams.model,
                'method': 'action_cancel',
                'args': [[self.actionParams.pickingId]],
            }).then(function () {
                self.trigger_up('exit');
            });
        });
    },

    /**
     * Makes the rpc to `button_scrap`.
     *
     * @private
     */
    _scrap: function () {
        var self = this;
        return self._save().then(function () {
            return self._rpc({
                'model': 'stock.picking',
                'method': 'button_scrap',
                'args': [[self.actionParams.pickingId]],
            }).then(function(res) {
                return self.do_action(res);
            });
        });
    },

    /**
     * @override
     */
    _applyChanges: function (changes) {
        var formattedCommands = [];
        var cmd = [];
        for (var i in changes) {
            var line = changes[i];
            if (line.id) {
                // Line needs to be updated
                cmd = [1, line.id, {
                    'qty_done' : line.qty_done,
                    'location_id': line.location_id.id,
                    'location_dest_id': line.location_dest_id.id,
                    'lot_id': line.lot_id && line.lot_id[0],
                    'lot_name': line.lot_name,
                }];
                formattedCommands.push(cmd);
            } else {
                // Line needs to be created
                cmd = [0, 0, {
                    'picking_id': line.picking_id,
                    'product_id':  line.product_id.id,
                    'product_uom_id': line.product_uom_id[0],
                    'qty_done': line.qty_done,
                    'location_id': line.location_id.id,
                    'location_dest_id': line.location_dest_id.id,
                    'lot_name': line.lot_name,
                    'lot_id': line.lot_id && line.lot_id[0],
                    'state': 'assigned',
                }];
                formattedCommands.push(cmd);
            }
        }
        if (formattedCommands.length > 0){
            return this._rpc({
                'model': this.actionParams.model,
                'method': 'write',
                'args': [[this.currentState.id], {
                    'move_line_ids': formattedCommands,
                }],
            });
        } else {
            return $.Deferred().reject();
        }
    },

    /**
     * @override
     */
    _showInformation: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            if (self.formWidget) {
                self.formWidget.destroy();
            }
            self.linesWidget.destroy();
            self.formWidget = new FormWidget(
                self,
                'stock.picking',
                'stock_barcode.stock_picking_barcode',
                {},
                self.currentState.id,
                'readonly'
            );
            self.formWidget.appendTo(self.$el);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles the `validate` OdooEvent. It makes an RPC call
     * to the method 'button_validate' to validate the current picking
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onValidate: function (ev) {
        ev.stopPropagation();
        var self = this;
        this.mutex.exec(function () {
            return self._save().then(function () {
                return self._validate();
            });
        });
    },

    /**
     * Handles the `cancel` OdooEvent. It makes an RPC call
     * to the method 'action_cancel' to cancel the current picking
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCancel: function (ev) {
        ev.stopPropagation();
        var self = this;
        this.mutex.exec(function () {
            return self._save().then(function () {
                return self._cancel();
            });
        });
    },

    /**
     * Handles the `print_picking` OdooEvent. It makes an RPC call
     * to the method 'do_print_picking'.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onPrintPicking: function (ev) {
        ev.stopPropagation();
        var self = this;
        this.mutex.exec(function () {
            return self._save().then(function () {
                return self._rpc({
                    'model': 'stock.picking',
                    'method': 'do_print_picking',
                    'args': [[self.actionParams.pickingId]],
                }).then(function(res) {
                    return self.do_action(res);
                });
            });
        });
    },

    /**
     * Handles the `print_delivery_slip` OdooEvent. It makes an RPC call
     * to the method 'do_action' on a 'ir.action_window' with the additional context
     * needed
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onPrintDeliverySlip: function (ev) {
        ev.stopPropagation();
        var self = this;
        this.mutex.exec(function () {
            return self._save().then(function () {
                return self.do_action(self.currentState.actionReportDeliverySlipId, {
                    'additional_context': {
                        'active_id': self.actionParams.pickingId,
                        'active_ids': [self.actionParams.pickingId],
                        'active_model': 'stock.picking',
                    }
                });
            });
        });
    },

    /**
     * Handles the `scan` OdooEvent. It makes an RPC call
     * to the method 'button_scrap' to scrap a picking.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onScrap: function (ev) {
        ev.stopPropagation();
        var self = this;
        this.mutex.exec(function () {
            return self._save().then(function () {
                return this._scrap();
            });
        });
    },
});

core.action_registry.add('stock_barcode_picking_client_action', PickingClientAction);

return PickingClientAction;

});
