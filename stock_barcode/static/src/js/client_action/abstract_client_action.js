odoo.define('stock_barcode.ClientAction', function (require) {
'use strict';

var concurrency = require('web.concurrency');
var core = require('web.core');
var AbstractAction = require('web.AbstractAction');

var FormWidget = require('stock_barcode.FormWidget');
var HeaderWidget = require('stock_barcode.HeaderWidget');
var LinesWidget = require('stock_barcode.LinesWidget');
var SettingsWidget = require('stock_barcode.SettingsWidget');
var utils = require('web.utils');

var _t = core._t;

function isChildOf(locationParent, locationChild) {
    return _.str.startsWith(locationChild.parent_path, locationParent.parent_path);
}

var ClientAction = AbstractAction.extend({
    className: 'barcode_client_action',
    custom_events: {
        show_information: '_onShowInformation',
        show_settings: '_onShowSettings',
        exit: '_onExit',
        edit_line: '_onEditLine',
        add_line: '_onAddLine',
        next_page: '_onNextPage',
        previous_page: '_onPreviousPage',
        reload: '_onReload',
    },

    init: function (parent, action) {
        this._super.apply(this, arguments);

        // We keep a copy of the action's parameters in order to make the calls to `this._getState`.
        this.actionParams = {
            pickingId: action.params.picking_id,
            inventoryId: action.params.inventory_id,
            model: action.params.model,
        };

        // Temp patch for the height issue
        this.actionManager = parent;
        this.actionManagerInitHeight = this.actionManager.$el.height;
        this.actionManager.$el.height('100%');

        this.mutex = new concurrency.Mutex();

        this.commands = {
            'O-CMD.PREV': this._previousPage.bind(this),
            'O-CMD.NEXT': this._nextPage.bind(this),
        };

        // State variables
        this.initialState = {};     // Will be filled by getState.
        this.currentState = {};     // Will be filled by getState and updated when operations occur.
        this.pages = [];            // Groups separating the pages.
        this.currentPageIndex = 0;  // The displayed page index related to `this.pages`.
        this.groups = {};
        this.title = this.actionParams.model === 'stock.inventory' ? // title of
            _('Inventory ') : ''; // the main navbar

        this.mode = undefined;      // supported mode: `receipt`, `internal`, `delivery`, `inventory`
        this.scannedLocation = undefined;
        this.scannedLines = [];
        this.scannedLocationDest = undefined;

        // Steps
        this.currentStep = undefined;
        this.stepsByName = {};
        for (var m in this) {
            if (typeof this[m] === 'function' && _.str.startsWith(m, '_step_')) {
                this.stepsByName[m.split('_step_')[1]] = this[m].bind(this);
            }
        }
    },

    willStart: function () {
        var self = this;
        var recordId = this.actionParams.pickingId || this.actionParams.inventoryId;
        return $.when(
            self._super.apply(self, arguments),
            self._getState(recordId),
            self._getProductBarcodes(),
            self._getLocationBarcodes()
        );
    },

    start: function () {
        var self = this;
        core.bus.on('barcode_scanned', this, this._onBarcodeScannedHandler);

        this.headerWidget = new HeaderWidget(this);
        this.settingsWidget = new SettingsWidget(this, this.actionParams.model, this.mode);
        return this._super.apply(this, arguments).then(function () {
            self.headerWidget.prependTo(self.$el);
            self.settingsWidget.appendTo(self.$el);
            self.settingsWidget.do_hide();
            return self._save();
        }).then(function () {
            self._reloadLineWidget(self.currentPageIndex);
        });
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Make an rpc to get the state and afterwards set `this.currentState` and `this.initialState`.
     * It also completes `this.title`.
     *
     * @private
     * @param {Object} [recordID] Id of the active picking or inventory adjustment.
     * @return {Deferred}
     */
    _getState: function (recordId) {
        var self = this;
        return this._rpc({
            'model': self.actionParams.model,
            'method': 'get_barcode_view_state',
            'args': [[recordId]],
        }).then(function (res) {
            self.currentState = res[0];
            self.initialState = $.extend(true, {}, res[0]);
            self.title += self.initialState.name;
            self.groups = {
                'group_stock_multi_locations': self.currentState.group_stock_multi_locations,
                'group_tracking_owner': self.currentState.group_tracking_owner,
                'group_tracking_lot': self.currentState.group_tracking_lot,
                'group_production_lot': self.currentState.group_production_lot,
                'group_uom': self.currentState.group_uom,
            };
        });
    },

    /**
     * Make an rpc to get the products barcodes and afterwards set `this.productsByBarcode`.
     *
     * @private
     * @return {Deferred}
     */
    _getProductBarcodes: function () {
        var self = this;
        return this._rpc({
            'model': 'product.product',
            'method': 'get_all_products_by_barcode',
            'args': [[]],
        }).then(function (res) {
            self.productsByBarcode = res;
        });
    },

    /**
     * Make an rpc to get the locations barcodes and afterwards set `this.locationsByBarcode`.
     *
     * @private
     * @return {Deferred}
     */
    _getLocationBarcodes: function () {
        var self = this;
        return this._rpc({
            'model': 'stock.location',
            'method': 'get_all_locations_by_barcode',
            'args': [[]],
        }).then(function (res) {
            self.locationsByBarcode = res;
        });
    },

    /**
     * Return an array of objects representing the lines displayed in `this.linesWidget`.
     * To implement by specialized client action.
     * actions.
     *
     * @abstract
     * @private
     * @returns {Array} array of objects (lines) to be displayed
     */
    _getLines: function (state) {  // jshint ignore:line
        return [];
    },

    /**
     * Return an array of string used to group the lines into pages. The string are keys the
     * `lines` objects.
     * To implement by specialized client actions.
     *
     * @abstract
     * @private
     * @returns {Array} array of fields to group (a group is actually a page)
     */
    _getPageFields: function () {
        return [];
    },

    /**
     * Return an array string representing the keys of `lines` objects the client action is
     * allowed to write on. It ll be used by `this._compareStates` to generate the write commands.
     * To implement by specialized client actions.
     *
     * @abstract
     * @private
     * @returns {Array} array of fields that can be scanned or modified
     */
    _getWriteableFields: function () {
        return [];
    },

    /**
     * Will compare `this._getLines(this.initialState)` and `this._getLines(this.currentState)` to
     * get created or modified lines. The result of this method will be used by `this._applyChanges`
     * to actually make the RPC call that will write the update values to the database.
     *
     * New lines are always pushed at the end of `this._getLines(this.currentState)`, so we assume
     * all lines having a greater index than the higher one in `_getLines(this.initialState)` are
     * new.
     *
     * @private
     * @returns {Array} array of objects representing the new or modified lines
     */
    _compareStates: function () {
        var modifiedMovelines = [];
        var writeableFields = this._getWriteableFields();

        // Get the modified lines.
        for (var i = 0; i < this._getLines(this.initialState).length; i++) {
            var currentLine = this._getLines(this.currentState)[i];
            var initialLine = this._getLines(this.initialState)[i];
            for (var j = 0; j < writeableFields.length; j++) {
                var writeableField = writeableFields[j];
                if (initialLine[writeableField] !== currentLine[writeableField] ) {
                    modifiedMovelines.push(currentLine);
                    break;
                }
            }
        }

        // Get the new lines.
        if (this._getLines(this.initialState).length < this._getLines(this.currentState).length) {
            modifiedMovelines = modifiedMovelines.concat(
                this._getLines(this.currentState).slice(this._getLines(this.initialState).length)
            );
        }
        return modifiedMovelines;
    },

    /**
     * Helper used in `this._onShowInformation`. This should be overidden by specialized client
     * actions to display something, usually a form view. What this method does is display
     * `this.headerWidget` into specialized mode and return the save Deferred.
     *
     * @private
     * @returns {Deferred}
     */
    _showInformation: function () {
        this.headerWidget.toggleDisplayContext('specialized');
        return this._save();
    },

    /**
     * Build a list of command from `changes` and make the `write` rpc.
     * To implement by specialized client actions.
     *
     * @private
     * @param {Array} changes lines in the current record needing to be created or updated
     * @returns {$.Deferred} resolved when the rpc is done ; failed if nothing has to be updated
     */
    _applyChanges: function (changes) {  // jshint ignore:line
        return $.when();
    },

    /**
     * This method will return a list of pages with grouped by source and destination locations from
     * `this.currentState.lines`. We may add pages not related to the lines in the following cases:
     *   - if there isn't any lines yet, we create a group with the default source and destination
     *     location of the picking
     *   - if the user scanned a different source location than the one in the current page, we'll
     *     create a page with the scanned source location and the default destination location of
     *     the picking.
     *
     * We do not need to apply the second logic in the case the user scans a destination location
     * in a picking client action as the lines will be impacted before calling this method.
     *
     * This method will *NOT* update `this.currentPageIndex`.
     *
     * @private
     * @returns {Array} array of objects representing the pages
     */
    _makePages: function () {
        var pages = [];
        var defaultPage = {};
        var self = this;
        if (this._getLines(this.currentState).length) {
            // from https://stackoverflow.com/a/25551041
            var groups = _.groupBy(this._getLines(this.currentState), function (line) {
                return _.map(self._getPageFields(), function (field) {
                    return utils.into(line, field[1]);
                }).join('#');
            });
            pages = _.map(groups, function (group) {
                var page = {};
                _.map(self._getPageFields(), function (field) {
                    page[field[0]] = utils.into(group[0], field[1]);
                });
                page.lines = group;
                return page;
            });
        } else {
            _.each(self._getPageFields(), function (field) {
                defaultPage[field[0]] = utils.into(self.currentState, field[1]);
            });
            defaultPage.lines = [];
        }
        pages = _.sortBy(pages, 'location_name');

        var currentPage = this.pages[this.currentPageIndex];
        // FIXME: what if already present in pages?
        if (this.scanned_location && currentPage.location_id !== this.scanned_location.id) {
            var pageValues = {
                location_id: this.scanned_location.id,
                location_name: this.scanned_location.name,
                lines: [],
            };
            if (self.actionParams.model === 'stock.picking') {
                pageValues.location_dest_id = this.currentState.location_dest_id.id;
                pageValues.location_dest_name = this.currentState.location_dest_id.name;
            }
            pages.push(pageValues);
        }

        if (pages.length === 0) {
            pages.push(defaultPage);
        }

        return pages;
    },

    /**
     * String identifying lines created in the client actions.

     * @private
     * @returns {string}
     */
    _getNewVirtualId: function () {
        return _.uniqueId('virtual_line_');
    },

    /**
     * Helper to create a new line.
     * To implement by specialized client actions.
     *
     * @abstract
     * @private
     * @param {Object} product product on the new line
     * @param {Object} barcode barcode of the product
     * @param {Object} qty_done
     * @returns {object} created line
     */
    _makeNewLine: function (product, barcode, qty_done) {  // jshint ignore:line
        return {};
    },

    /**
     * Refresh the displayed page/lines on the screen. It destroys and reinstantiate
     * `this.linesWidget`.
     *
     * @private
     * @param {Object} pageIndex page index
     */
     _reloadLineWidget: function (pageIndex) {
        if (this.linesWidget) {
            this.linesWidget.destroy();
        }
        var nbPages = this.pages.length;
        var preparedPage = $.extend(true, {}, this.pages[pageIndex]);
        this.linesWidget = new LinesWidget(this, preparedPage, pageIndex, nbPages);
        this.linesWidget.appendTo(this.$el);
    },

    /**
     * Main method to make the changes done in the client action persistent in the database through
     * RPC calls. It'll compare `this.currentState` to `this.initialState`, make an RPC with the
     * commands generated by the previous step, re-read the `this.model` state, re-prepare the
     * groups and move `this.currentIndex` to the page of the same group. It also tries to not make
     * an RPC if there aren't changes to save.
     *
     * @private
     * @param {Object} params.forceReload boolean to know if we want to force a read even if no
     *   changes were found.
     * @param {Object} params.new_location_id new source location on the line
     * @param {Object} params.new_location_dest_id new destinationlocation on the line
     * @returns {Deferred}
     */
    _save: function (params) {
        params = params || {};
        var self = this;

        // keep a reference to the currentGroup
        var currentPage = this.currentPageIndex ? this.pages[this.currentPageIndex] : {};
        var currentLocationId = currentPage.location_id;
        var currentLocationDestId = currentPage.location_dest_id;

        // make a write with the current changes
        var recordId = this.actionParams.pickingId || this.actionParams.inventoryId;
        var applyChangesDef =  this._applyChanges(this._compareStates()).then(function () {
            return self._getState(recordId);
        }, function () {
            if (params.forceReload) {
                return self._getState(recordId);
            } else {
                return $.when();
            }
        });

        return applyChangesDef.then(function () {
            self.pages = self._makePages();
            var newPageIndex = _.findIndex(self.pages, function (page) {
                return page.location_id === (params.new_location_id || currentLocationId) &&
                    (self.actionParams.model === 'stock.inventory' ||
                    page.location_dest_id === (params.new_location_dest_id || currentLocationDestId));
            }) || 0;
            if (newPageIndex === -1) {
                newPageIndex = 0;
            }
            self.currentPageIndex = newPageIndex;
        });
    },

    /**
     * Handles the actions when a barcode is scanned, mainly by executing the appropriate step. If
     * we need to change page after the step is executed, it calls `this._save` and
     * `this._reloadLineWidget` with the new page index. Afterwards, we apply the appropriate logic
     * to `this.linesWidget`.
     *
     * @private
     * @param {String} barcode the scanned barcode
     * @returns Deferred
     */
    _onBarcodeScanned: function (barcode) {
        var self = this;
        return this.stepsByName[this.currentStep || 'source'](barcode, []).then(function (res) {
            /* We check now if we need to change page. If we need to, we'll call `this.save` with the
             * `new_location_id``and `new_location_dest_id` params so `this.currentPage` will
             * automatically be on the new page. We need to change page when we scan a source or a
             * destination location ; if the source or destination is different than the current
             * page's one.
             */
            var def = $.when();
            var currentPage = self.pages[self.currentPageIndex];
            if (
                (self.scanned_location &&
                 ! self.scannedLines.length &&
                 self.scanned_location.id !== currentPage.location_id
                ) ||
                (self.scanned_location_dest &&
                 self.scannedLines.length &&
                 self.scanned_location_dest.id !== currentPage.location_dest_id
                )
            ) {
                // The expected locations are the scanned locations or the default picking locations.
                var expectedLocationId = self.scanned_location.id;
                var expectedLocationDestId;
                if (self.actionParams.model === 'stock.picking'){
                    expectedLocationDestId = self.scanned_location_dest &&
                                             self.scanned_location_dest.id ||
                                             self.currentState.location_dest_id.id;
                }

                if (expectedLocationId !== currentPage.location_id ||
                    expectedLocationDestId !== currentPage.location_dest_id
                ) {
                    var params = {
                        new_location_id: expectedLocationId,
                    };
                    if (expectedLocationDestId) {
                        params.new_location_dest_id = expectedLocationDestId;
                    }
                    def = self._save(params).then(function () {
                        self._reloadLineWidget(self.currentPageIndex);
                    });
                }
            }

            // Apply now the needed actions on the different widgets.
            if (self.scannedLines && self.scanned_location_dest) {
                self._endBarcodeFlow();
            }
            var linesActions = res.linesActions;
            def.always(function () {
                _.each(linesActions, function (action) {
                    action[0].apply(self.linesWidget, action[1]);
                });
                return $.when();
            });
            return def;
        }, function (errorMessage) {
            self.do_warn(_t('Warning'), errorMessage);
        });
    },

    /**
     * Clear the states variables of the barcode flow. It should be used before beginning a new
     * flow.
     *
     * @private
     */
    _endBarcodeFlow: function () {
        this.scanned_location = undefined;
        this.scannedLines = [];
        this.scanned_location_dest = undefined;
        this.currentStep = undefined;
    },

    /**
     * Loop over the lines displayed in the current pages and try to find a candidate to increment
     * according to the `params` argument.
     *
     * @private
     * @param {Object} params information needed to find the candidate line
     * @param {Object} params.product
     * @param {Object} params.lot_id
     * @param {Object} params.lot_name
     * @returns object|boolean line or false if nothing match
     */
    _findCandidateLineToIncrement: function (params) {
        var product = params.product;
        var lotId = params.lot_id;
        var lotName = params.lot_name;
        var currentPage = this.pages[this.currentPageIndex];
        var res = false;
        for (var z = 0; z < currentPage.lines.length; z++) {
            var lineInCurrentPage = currentPage.lines[z];
            if (lineInCurrentPage.product_id.id === product.id) {
                // If the line is empty, we could re-use it.
                if (lineInCurrentPage.virtual_id &&
                    (this.actionParams.model === 'stock.picking' &&
                     ! lineInCurrentPage.qty_done &&
                     ! lineInCurrentPage.product_uom_qty &&
                     ! lineInCurrentPage.lot_id &&
                     !lineInCurrentPage.lot_name
                    ) ||
                    (this.actionParams.model === 'stock.inventory' &&
                     ! lineInCurrentPage.product_qty &&
                     ! lineInCurrentPage.prod_lot_id
                    )
                ) {
                    res = lineInCurrentPage;
                    break;
                }

                if (product.tracking === 'serial' &&
                    ((this.actionParams.model === 'stock.picking' &&
                      lineInCurrentPage.qty_done > 0
                     ) ||
                    (this.actionParams.model === 'stock.inventory' &&
                     lineInCurrentPage.product_qty > 0
                    ))) {
                    continue;
                }
                if (lineInCurrentPage.qty_done &&
                (this.actionParams.model === 'stock.inventory' ||
                lineInCurrentPage.location_dest_id.id === currentPage.location_dest_id) &&
                this.scannedLines.indexOf(lineInCurrentPage.virtual_id || lineInCurrentPage.id) === -1 &&
                lineInCurrentPage.qty_done >= lineInCurrentPage.product_uom_qty) {
                    continue;
                }
                if (lotId &&
                    ((this.actionParams.model === 'stock.picking' &&
                     lineInCurrentPage.lot_id &&
                     lineInCurrentPage.lot_id[0] !== lotId
                     ) ||
                    (this.actionParams.model === 'stock.inventory' &&
                     lineInCurrentPage.prod_lot_id &&
                     lineInCurrentPage.prod_lot_id[0] !== lotId
                    )
                )) {
                    continue;
                }
                if (lotName &&
                    lineInCurrentPage.lot_name &&
                    lineInCurrentPage.lot_name !== lotName
                    ) {
                    continue;
                }
                res = lineInCurrentPage;
                break;
            }
        }
        return res;
    },

    /**
     * Main method called when a quantity needs to be incremented or a lot set on a line.
     * it calls `this._findCandidateLineToIncrement` first, if nothing is found it may use
     * `this._makeNewLine`.
     *
     * @private
     * @param {Object} params information needed to find the potential candidate line
     * @param {Object} params.product
     * @param {Object} params.lot_id
     * @param {Object} params.lot_name
     * @return {object} object wrapping the incremented line and some other informations
     */
    _incrementLines: function (params) {
        var line = this._findCandidateLineToIncrement(params);
        var isNewLine = false;
        if (line) {
            // Update the line with the processed quantity.
            if (params.product.tracking === 'none' ||
                params.lot_id ||
                params.lot_name
                ) {
                if (this.actionParams.model === 'stock.picking') {
                    line.qty_done++;
                } else if (this.actionParams.model === 'stock.inventory') {
                    line.product_qty++;
                }
            }
        } else {
            isNewLine = true;
            // Create a line with the processed quantity.
            if (params.product.tracking === 'none' ||
                params.lot_id ||
                params.lot_name
                ) {
                line = this._makeNewLine(params.product, params.barcode, 1);
            } else {
                line = this._makeNewLine(params.product, params.barcode, 0);
            }
            this._getLines(this.currentState).push(line);
            this.pages[this.currentPageIndex].lines.push(line);
        }
        if (this.actionParams.model === 'stock.picking') {
            if (params.lot_id) {
                line.lot_id = [params.lot_id];
            }
            if (params.lot_name) {
                line.lot_name = params.lot_name;
            }
        } else if (this.actionParams.model === 'stock.inventory') {
            if (params.lot_id) {
                line.prod_lot_id = [params.lot_id, params.lot_name];
            }
        }
        return {
            'id': line.id,
            'virtualId': line.virtual_id,
            'lineDescription': line,
            'isNewLine': isNewLine,
        };
    },

    // -------------------------------------------------------------------------
    // Private: flow steps
    // -------------------------------------------------------------------------

    /**
     * Handle what needs to be done when a source location is scanned.
     *
     * @param {string} barcode scanned barcode
     * @param {Object} linesActions
     * @returns {Deferred}
     */
    _step_source: function (barcode, linesActions) {
        this.currentStep = 'source';
        var errorMessage;

        // Bypass the step if needed.
        if (this.mode === 'receipt' || this.mode === 'no_multi_locations') {
            this.scanned_location = this.currentState.location_id;
            return this._step_product(barcode, linesActions);
        }

        var sourceLocation = this.locationsByBarcode[barcode];
        if (sourceLocation) {
            if (! isChildOf(this.currentState.location_id, sourceLocation)) {
                errorMessage = _t('This location is not a child of the main location.');
                return $.Deferred().reject(errorMessage);
            } else {
                // There's nothing to do on the state here, just mark `this.scanned_location`.
                linesActions.push([this.linesWidget.highlightLocation, [true]]);
                if (this.actionParams.model === 'stock.picking') {
                    linesActions.push([this.linesWidget.highlightDestinationLocation, [false]]);
                }
                this.scanned_location = sourceLocation;
                this.currentStep = 'product';
                return $.when({linesActions: linesActions});
            }
        } else {
            errorMessage = _t('You are expected to scan a source location.');
            return $.Deferred().reject(errorMessage);
        }
    },

    /**
     * Handle what needs to be done when a product is scanned.
     *
     * @param {string} barcode scanned barcode
     * @param {Object} linesActions
     * @returns {Deferred}
     */
    _step_product: function (barcode, linesActions) {
        this.currentStep = 'product';
        var errorMessage;

        var product = this.productsByBarcode[barcode];
        if (product) {
            if (product.tracking !== 'none') {
                this.currentStep = 'lot';
            }
            var res = this._incrementLines({'product': product, 'barcode': barcode});
            if (res.isNewLine) {
                linesActions.push([this.linesWidget.addProduct, [res.lineDescription, this.actionParams.model]]);
            } else {
                if (product.tracking === 'none') {
                    linesActions.push([this.linesWidget.incrementProduct, [res.id || res.virtualId, 1, this.actionParams.model]]);
                } else {
                    linesActions.push([this.linesWidget.incrementProduct, [res.id || res.virtualId, 0, this.actionParams.model]]);
                }
            }
            this.scannedLines.push(res.id || res.virtualId);
            return $.when({linesActions: linesActions});
        } else {
            if (! this.scannedLines.length) {
                errorMessage = _t('You are expected to scan one or more products.');
                return $.Deferred().reject(errorMessage);
            }
            var destinationLocation = this.locationsByBarcode[barcode];
            if (destinationLocation) {
                return this._step_destination(barcode, linesActions);
            } else {
                errorMessage = _t('You are expected to scan more products or a destination location.');
                return $.Deferred().reject(errorMessage);
            }
        }
    },

    /**
     * Handle what needs to be done when a lot is scanned.
     *
     * @param {string} barcode scanned barcode
     * @param {Object} linesActions
     * @returns {Deferred}
     */
    _step_lot: function (barcode, linesActions) {
        this.currentStep = 'lot';
        var errorMessage;
        var self = this;

        // Bypass this step if needed.
        if (this.productsByBarcode[barcode]) {
            return this._step_product(barcode, linesActions);
        } else if (this.locationsByBarcode[barcode]) {
            return this._step_destination(barcode, linesActions);
        }

        // Get product
        // Get the latest scanned line.
        var idOrVirtualId = this.scannedLines[this.scannedLines.length - 1];
        var line = _.find(self._getLines(self.currentState), function (line) {
            return line.virtual_id === idOrVirtualId || line.id === idOrVirtualId;
        });
        var product = this.productsByBarcode[line.product_barcode];


        var searchRead = function (barcode, product) {
            return self._rpc({
                model: 'stock.production.lot',
                method: 'search_read',
                domain: [['name', '=', barcode], ['product_id', '=', product.id]],
                limit: 1,
            });
        };

        var create = function (barcode, product_id) {
            return self._rpc({
                model: 'stock.production.lot',
                method: 'create',
                args: [{
                    'name': barcode,
                    'product_id': product_id.id,
                }],
            });
        };

        var def;
        if (this.currentState.use_create_lots &&
            ! this.currentState.use_existing_lots) {
            def = $.when({'lot_name': barcode});
        } else if (! this.currentState.use_create_lots &&
                    this.currentState.use_existing_lots) {
            def = searchRead(barcode, product).then( function (res) {
                if (! res.length){
                    errorMessage = _t('The scanned lot does not match an existing one.');
                    return $.Deferred().reject(errorMessage);
                }
                return $.when({ 'lot_id': res[0].id, 'lot_name': res[0].name});
            });
        } else {
            def = searchRead(barcode, product).then( function (res) {
                if (! res.length){
                    return create(barcode, product).then(function (lot_id) {
                        return $.when({'lot_id': lot_id, 'lot_name': barcode});
                    });
                }
                return $.when({ 'lot_id': res[0].id, 'lot_name': res[0].name});
            });
        }
        return def.then(function (lot_info) {
            var res = self._incrementLines({
                'product': product,
                'barcode': line.product_barcode,
                'lot_id': lot_info.lot_id,
                'lot_name': lot_info.lot_name
            });
            if (res.isNewLine) {
                self.scannedLines.push(res.lineDescription.virtual_id);
                linesActions.push([self.linesWidget.addProduct, [res.lineDescription, self.actionParams.model]]);
            } else {
                linesActions.push([self.linesWidget.incrementProduct, [res.id || res.virtualId, 1, self.actionParams.model]]);
                linesActions.push([self.linesWidget.setLotName, [res.id || res.virtualId, barcode]]);
            }
            return $.when({linesActions: linesActions});
        });
    },

    /**
     * Handle what needs to be done when a destination location is scanned.
     *
     * @param {string} barcode scanned barcode
     * @param {Object} linesActions
     * @returns {Deferred}
     */
    _step_destination: function (barcode, linesActions) {
        var errorMessage;

        // Bypass the step if needed.
        if (this.mode === 'delivery' || this.mode === 'no_multi_locations'  || this.actionParams.model === 'stock.inventory') {
            this._endBarcodeFlow();
            return this._step_source(barcode, linesActions);
        }

        var destinationLocation = this.locationsByBarcode[barcode];
        if (! isChildOf(this.currentState.location_dest_id, destinationLocation)) {
            errorMessage = _t('This location is not a child of the main location.');
            return $.Deferred().reject(errorMessage);
        } else {
            var self = this;
            // FIXME: remove .uniq() once the code is adapted.
            _.each(_.uniq(this.scannedLines), function (idOrVirtualId) {
                var currentStateLine = _.find(self._getLines(self.currentState), function (line) {
                    return line.virtual_id &&
                           line.virtual_id.toString() === idOrVirtualId ||
                           line.id  === idOrVirtualId;
                });
                if (currentStateLine.qty_done - currentStateLine.product_uom_qty >= 0) {
                    // Move the line.
                    currentStateLine.location_dest_id.id = destinationLocation.id;
                    currentStateLine.location_dest_id.name = destinationLocation.name;
                } else {
                    // Split the line.
                    var qty = currentStateLine.qty_done;
                    currentStateLine.qty_done -= qty;
                    var newLine = $.extend(true, {}, currentStateLine);
                    newLine.qty_done = qty;
                    newLine.location_dest_id.id = destinationLocation.id;
                    newLine.location_dest_id.name = destinationLocation.name;
                    newLine.product_uom_qty = 0;
                    var virtualId = self._getNewVirtualId();
                    newLine.virtual_id = virtualId;
                    delete newLine.id;
                    self._getLines(self.currentState).push(newLine);
                }
            });
            linesActions.push([this.linesWidget.clearLineHighlight, [undefined]]);
            linesActions.push([this.linesWidget.highlightLocation, [true]]);
            linesActions.push([this.linesWidget.highlightDestinationLocation, [true]]);
            this.scanned_location_dest = destinationLocation;
            return $.when({linesActions: linesActions});
        }
    },

    /**
     * Helper used when we want to go the next page. It calls `this._endBarcodeFlow`.
     *
     * @return {Deferred}
     */
    _nextPage: function (){
        var self = this;
        return this.mutex.exec(function () {
            return self._save().then(function () {
                if (self.currentPageIndex < self.pages.length - 1) {
                    self.currentPageIndex++;
                }
                self._reloadLineWidget(self.currentPageIndex);
                self._endBarcodeFlow();
            });
        });
    },

    /**
     * Helper used when we want to go the previous page. It calls `this._endBarcodeFlow`.
     *
     * @return {Deferred}
     */
    _previousPage: function () {
        var self = this;
        return this.mutex.exec(function () {
            return self._save().then(function () {
                if (self.currentPageIndex > 0) {
                    self.currentPageIndex--;
                } else {
                    self.currentPageIndex = self.pages.length - 1;
                }
                self._reloadLineWidget(self.currentPageIndex);
                self._endBarcodeFlow();
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles the barcode scan event. Dispatch it to the appropriate method if it is a
     * commande, else use `this._onBarcodeScanned`.
     *
     * @private
     * @param {String} barcode scanned barcode
     * @return {Deferred}
     */
    _onBarcodeScannedHandler: function (barcode) {
        var self = this;
        this.mutex.exec(function() {
            if (self.mode === 'done' || self.mode === 'cancel') {
                self.do_warn(_t('Warning'), _t('Scanning is disabled in this state.'));
                return $.when();
            }
            var commandeHandler = self.commands[barcode];
            if (commandeHandler) {
                return commandeHandler();
            }
            return self._onBarcodeScanned(barcode);
        });
    },

    /**
     * Handles the `exit` OdooEvent. We disable the fullscreen mode and trigger_up an
     * `history_back`.
     *
     * @private
     * @param {OdooEvent} ev
     */
     _onExit: function (ev) {
        ev.stopPropagation();
        var self = this;
        this.mutex.exec( function () {
            return self._save().then(function () {
                self.actionManager.$el.height(self.actionManagerInitHeight);
                self.trigger_up('toggle_fullscreen');
                self.trigger_up('history_back');
            });
        });
    },

    /**
     * Handles the `add_product` OdooEvent. It destroys `this.linesWidget` and displays an instance
     * of `FormWidget` for the line model.
     * `this.formWidget`
     *
     * @private
     * @param {OdooEvent} ev
     */
     _onAddLine: function (ev) {
        ev.stopPropagation();
        var self = this;
        this.mutex.exec(function () {
            self.linesWidget.destroy();
            self.headerWidget.toggleDisplayContext('specialized');
            return self._save().then(function () {
                self._endBarcodeFlow();
                if (self.actionParams.model === 'stock.picking') {
                    self.formWidget = new FormWidget(
                        self,
                        'stock.move.line',
                        'stock_barcode.stock_move_line_product_selector',
                        {
                            'default_picking_id': self.currentState.id,
                            'default_location_id': self.pages[self.currentPageIndex].location_id,
                            'default_location_dest_id': self.pages[self.currentPageIndex].location_dest_id,
                            'default_qty_done': 1,
                        },
                        false
                    );
                } else if (self.actionParams.model === 'stock.inventory') {
                    self.formWidget = new FormWidget(
                        self,
                        'stock.inventory.line',
                        'stock_barcode.stock_inventory_line_barcode',
                        {
                            'default_company_id': self.currentState.company_id[0],
                            'default_inventory_id': self.currentState.id,
                            'default_location_id': self.pages[self.currentPageIndex].location_id,
                            'default_product_qty': 1,
                        },
                        false
                    );
                }
                return self.formWidget.appendTo(self.$el);
            });
        });
    },

    /**
     * Handles the `edit_product` OdooEvent. It destroys `this.linesWidget` and displays an instance
     * of `FormWidget` for the line model.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onEditLine: function (ev) {
        ev.stopPropagation();
        this.linesWidget.destroy();
        this.headerWidget.toggleDisplayContext('specialized');

        // If we want to edit a not yet saved line, keep its description in a variable so we'll be
        // able to get it back once saved.
        var lineDescription = false;
        if (_.isString(ev.data.id)) {
            var currentPage = this.pages[this.currentPageIndex];
            lineDescription = _.findWhere(currentPage.lines, {virtual_id: ev.data.id});
        }

        var self = this;
        this.mutex.exec(function () {
            return self._save().then(function () {
                var id = ev.data.id;
                if (_.isString(id) && lineDescription) {
                    var currentPage = self.pages[self.currentPageIndex];
                    // FIXME use _.isEqual but the state there are missing keys...
                    var rec = _.find(currentPage.lines, function (line) {
                        return line.product_id.id === lineDescription.product_id.id &&
                            line.qty_done === lineDescription.qty_done;
                    });
                    id = rec.id;
                }
                if (self.actionParams.model === 'stock.picking') {
                    self.formWidget = new FormWidget(
                        self,
                        'stock.move.line',
                        'stock_barcode.stock_move_line_product_selector',
                        {},
                        id
                    );
                } else {
                    self.formWidget = new FormWidget(
                        self,
                        'stock.inventory.line',
                        'stock_barcode.stock_inventory_line_barcode',
                        {},
                        id
                    );
                }
                return self.formWidget.appendTo(self.$el);
            });
        });
    },

    /**
     * Handles the `show_information` OdooEvent. It hides the main widget and
     * display a standard form view with information about the current record.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onShowInformation: function (ev) {  // jshint ignore:line
        this._showInformation();
    },

    /**
     * Handles the `show_settings` OdooEvent. It hides `this.linesWidget` and dipslays
     * `this.settinsWidget`.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onShowSettings: function (ev) {
        ev.stopPropagation();
        var self = this;
        this.mutex.exec(function () {
            return self._save().then(function () {
                if (self.formWidget) {
                    self.formWidget.destroy();
                }
                if (self.linesWidget) {
                    self.linesWidget.destroy();
                }
                self.headerWidget.toggleDisplayContext('specialized');
                self.settingsWidget.do_show();
            });
        });
    },

    /**
     * Handles the `reload` OdooEvent.
     * Currently, this event is only triggered by `this.formWidget`.
     *
     * @private
     * @param {OdooEvent} ev ev.data could contain res_id
     */
    _onReload: function (ev) {
        ev.stopPropagation();
        if (this.formWidget) {
            this.formWidget.destroy();
        }
        if (this.settingsWidget) {
            this.settingsWidget.do_hide();
        }
        this.headerWidget.toggleDisplayContext('init');
        this.$('.o_show_information').toggleClass('o_hidden', false);
        var self = this;
        this._save({'forceReload': true}).then(function () {
            var record = ev.data.record;
            if (record) {

                var newPageIndex = _.findIndex(self.pages, function (page) {
                    return page.location_id === record.data.location_id.res_id &&
                           (self.actionParams.model === 'stock.inventory' ||
                            page.location_dest_id === record.data.location_dest_id.res_id);
                });
                if (newPageIndex === -1) {
                    new Error('broken');
                }
                self.currentPageIndex = newPageIndex;
            }
            self._reloadLineWidget(self.currentPageIndex);
            self._endBarcodeFlow();
        });
    },

    /**
     * Handles the `next_move` OdooEvent. It makes `this.linesWidget` display
     * the next group of lines.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onNextPage: function (ev) {
        ev.stopPropagation();
        this._nextPage();
    },

    /**
     * Handles the `previous_move` OdooEvent. It makes `this.linesWidget` display
     * the previous group of lines.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onPreviousPage: function (ev) {
        ev.stopPropagation();
        this._previousPage();
    },
});

core.action_registry.add('stock_barcode_client_action', ClientAction);

return ClientAction;

});
