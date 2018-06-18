odoo.define('test_barcode_flows.tour', function(require) {
'use strict';

var tour = require('web_tour.tour');

// ----------------------------------------------------------------------------
// Test helpers
// ----------------------------------------------------------------------------
function fail (errorMessage) {
    tour._consume_tour(tour.running_tour, errorMessage);
}

function getLine (description) {
    var $res;
    $('.line').each(function () {
        var $line = $(this);
        var barcode = $line.data('barcode').trim();
        if (description.barcode === barcode) {
            if ($res) {
                $res.add($line);
            } else {
                $res = $line;
            }
        }
    });
    if (! $res) {
        fail('cannot get the line');
    }
    return $res;
}

function assert (current, expected, info) {
    if (current !== expected) {
        fail(info + ': "' + current + '" instead of "' + expected + '".');
    }
}

function assertPageSummary (expected) {
    var $pageSummary = $('.barcode_locations');
    var current = $pageSummary.text();
    assert(current, expected, 'Page summary');
}

function assertPreviousVisible (expected) {
    var $previousButton = $('.o_previous_page');
    var current = $previousButton.hasClass('o_hidden');
    assert(!current, expected, 'Previous visible');
}

function assertPreviousEnabled (expected) {
    var $previousButton = $('.o_previous_page');
    var current = $previousButton.prop('disabled');
    assert(!current, expected, 'Previous button enabled');
}

function assertNextVisible (expected) {
    var $nextButton = $('.o_next_page');
    var current = $nextButton.hasClass('o_hidden');
    assert(!current, expected, 'Next visible');
}

function assertNextEnabled (expected) {
    var $nextButton = $('.o_next_page');
    var current = $nextButton.prop('disabled');
    assert(!current, expected, 'Next button enabled');
}

function assertNextIsHighlighted (expected) {
    var $nextButton = $('.o_next_page');
    var current = $nextButton.hasClass('o_button_barcode_highlight');
    assert(current, expected, 'Next button is highlighted');
}

function assertValidateVisible (expected) {
    var $validate = $('.o_validate_page');
    var current = $validate.hasClass('o_hidden');
    assert(!current, expected, 'Validate visible');
}

function assertValidateEnabled (expected) {
    var $validate = $('.o_validate_page');
    var current = $validate.prop('disabled');
    assert(!current, expected, 'Validate enabled');
}

function assertValidateIsHighlighted (expected) {
    var $validate = $('.o_validate_page');
    var current = $validate.hasClass('o_button_barcode_highlight');
    assert(current, expected, 'Validte button is highlighted');
}

function assertLinesCount (expected) {
    var $lines = $('.line');
    var current = $lines.length;
    assert(current, expected, "Number of lines");
}

function assertScanMessage (expected) {
    var $helps = $('.o_scan_message');
    var $help = $helps.filter('.o_scan_message_' + expected);
    if (! $help.length || $help.hasClass('o_hidden')) {
        fail('assertScanMessage: "' + expected + '" is not displayed');
    }
}

function assertLocationHighlight (expected) {
    var $locationElem = $('.o_barcode_summary_location_src');
    assert($locationElem.hasClass('o_strong'), expected, 'Location source is not bold');
}

function assertDestinationLocationHighlight (expected) {
    var $locationElem = $('.o_barcode_summary_location_dest');
    assert($locationElem.hasClass('o_strong'), expected, 'Location destination is not bold');
}

function assertPager (expected) {
    var $pager = $('.barcode_move_number');
    assert($pager.text(), expected, 'Pager is wrong');
}

function assertLineIsHighlighted ($line, expected) {
    assert($line.hasClass('o_highlight'), expected, 'line should be highlighted');
}

function assertFormLocationSrc(expected) {
    var $location = $('.o_field_widget[name="location_id"] input')
    assert($location.val(), expected, 'Wrong source location')
}

function assertFormLocationDest(expected) {
    var $location = $('.o_field_widget[name="location_dest_id"] input')
    assert($location.val(), expected, 'Wrong destination location')
}
function assertFormQuantity(expected) {
    var $location = $('.o_field_widget[name="qty_done"]')
    assert($location.val(), expected, 'Wrong destination location')

}

function assertInventoryFormQuantity(expected) {
    var $location = $('.o_field_widget[name="product_qty"]')
    assert($location.val(), expected, 'Wrong quantity')

}

// ----------------------------------------------------------------------------
// Tours
// ----------------------------------------------------------------------------
tour.register('test_internal_picking_from_scratch_1', {test: true}, [
    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Stock To Stock');
            assertPreviousVisible(true);
            assertPreviousEnabled(false);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(0);
            assertScanMessage('scan_src');
            assertLocationHighlight(false);
            assertDestinationLocationHighlight(false);
            assertPager('1/1');
            assertValidateVisible(true);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(false);
        }
    },

    /* We'll create a movement for 2 product1 from shelf1 to shelf2. The flow for this to happen is
     * to scan shelf1, product1, shelf2.
     */
    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.barcode_client_action',
        run: function () {
            assertPageSummary('From Shelf 1 To Stock');
            assertPreviousVisible(true);
            assertPreviousEnabled(false);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(0);
            assertScanMessage('scan_products');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(false);
            assertPager('1/1');
            assertValidateVisible(true);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(false);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 1 To Stock');
            assertPreviousVisible(true);
            assertPreviousEnabled(false);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(1);
            assertScanMessage('scan_more_dest');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(false);
            assertPager('1/1');
            assertValidateVisible(true);
            assertValidateIsHighlighted(true);
            assertValidateEnabled(true);
            var $line = getLine({barcode: 'product1'});
            assertLineIsHighlighted($line, true);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 1 To Stock');
            assertPreviousVisible(true);
            assertPreviousEnabled(false);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(1);
            assertScanMessage('scan_more_dest');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(false);
            assertPager('1/1');
            assertValidateVisible(true);
            assertValidateIsHighlighted(true);
            assertValidateEnabled(true);
            var $line = getLine({barcode: 'product1'});
            assertLineIsHighlighted($line, true);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-02-00'
    },

    {
        trigger: '.o_barcode_summary_location_dest:contains("Shelf 2")',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 2');
            assertPreviousVisible(true);
            assertPreviousEnabled(false);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(1);
            assertScanMessage('scan_src');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(true);
            assertPager('1/1');
            assertValidateVisible(true);
            assertValidateIsHighlighted(true);
            assertValidateEnabled(true);
            var $line = getLine({barcode: 'product1'});
            assertLineIsHighlighted($line, false);
        }
    },

    /* We'll create a movement for product2 from shelf1 to shelf3. The flow for this to happen is
     * to scan shelf1, product2, shelf3.
     */
    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 2');
            assertPreviousVisible(true);
            assertPreviousEnabled(false);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(1);
            assertScanMessage('scan_products');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(false);
            assertPager('1/1');
            assertValidateVisible(true);
            assertValidateIsHighlighted(true);
            assertValidateEnabled(true);
            var $line = getLine({barcode: 'product1'});
            assertLineIsHighlighted($line, false);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 2');
            assertPreviousVisible(true);
            assertPreviousEnabled(false);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(2);
            assertScanMessage('scan_more_dest');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(false);
            assertPager('1/1');
            assertValidateVisible(true);
            assertValidateIsHighlighted(true);
            assertValidateEnabled(true);
            var $lineproduct1 = getLine({barcode: 'product1'});
            assertLineIsHighlighted($lineproduct1, false);
            var $lineproduct2 = getLine({barcode: 'product2'});
            assertLineIsHighlighted($lineproduct2, true);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan shelf3'
    },

    {
        trigger: '.o_barcode_summary_location_dest:contains("Shelf 3")',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 3');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(1);
            assertScanMessage('scan_src');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(true);
            assertPager('2/2');
            assertValidateVisible(true);
            assertValidateIsHighlighted(true);
            assertValidateEnabled(true);
            var $lineproduct2 = getLine({barcode: 'product2'});
            assertLineIsHighlighted($lineproduct2, false);
        }
    },

    /* We'll now move a product2 from shelf1 to shelf2. As we're still on the shel1 to shelf3 page
     * where a product2 was processed, we make sure the newly scanned product will be added in a
     * new move line that will change page at the time we scan shelf2.
     */
    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 3');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(1);
            assertScanMessage('scan_products');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(false);
            assertPager('2/2');
            assertValidateVisible(true);
            assertValidateIsHighlighted(true);
            assertValidateEnabled(true);
            var $lineproduct2 = getLine({barcode: 'product2'});
            assertLineIsHighlighted($lineproduct2, false);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 3');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(2);
            assertScanMessage('scan_more_dest');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(false);
            assertPager('2/2');
            assertValidateVisible(true);
            assertValidateIsHighlighted(true);
            assertValidateEnabled(true);
            var $lines = getLine({barcode: 'product2'});
            if ($lines.filter('.o_highlight').length !== 1) {
                fail('one of the two lins of product2 should be highlighted.');
            }
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-02-00'
    },

    {
        trigger: '.o_barcode_summary_location_dest:contains("Shelf 2")',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 2');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(true);
            assertNextEnabled(true);
            assertNextIsHighlighted(true);
            assertLinesCount(2);
            assertScanMessage('scan_src');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(true);
            assertPager('1/2');
            assertValidateVisible(false);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(false);
            var $line = getLine({barcode: 'product1'});
            assertLineIsHighlighted($line, false);
        }
    },
]);

tour.register('test_internal_picking_from_scratch_2', {test: true}, [
    /* Move 2 product1 from shelf 1 to shelf 2.
     */
    {
        trigger: '.o_add_line',
    },

    {
        extra_trigger: '.o_form_label:contains("Product")',
        trigger: "input.o_field_widget[name=qty_done]",
        run: 'text 2',
    },

    {
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text product1',
    },

    {
        trigger: ".ui-menu-item > a:contains('product1')",
    },

    {
        trigger: ".o_field_widget[name=location_id] input",
        run: 'text Shelf 1',
    },

    {
        trigger: ".ui-menu-item > a:contains('Shelf 1')",
    },

    {
        trigger: ".o_field_widget[name=location_dest_id] input",
        run: 'text Shelf 2',
    },

    {
        trigger: ".ui-menu-item > a:contains('Shelf 2')",
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_barcode_summary_location_dest:contains("Shelf 2")',
        run: function() {
            assertLinesCount(1);
        },
    },

    /* Move 1 product2 from shelf 1 to shelf 3.
     */
    {
        trigger: '.o_add_line',
    },

    {
        extra_trigger: '.o_form_label:contains("Product")',
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text product2',
    },

    {
        trigger: ".ui-menu-item > a:contains('product2')",
    },

    {
        trigger: ".o_field_widget[name=location_id] input",
        run: 'text Shelf 1',
    },

    {
        trigger: ".ui-menu-item > a:contains('Shelf 1')",
    },

    {
        trigger: ".o_field_widget[name=location_dest_id] input",
        run: 'text Shelf 3',
    },

    {
        trigger: ".ui-menu-item > a:contains('Shelf 3')",
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_barcode_summary_location_dest:contains("Shelf 3")',
        run: function() {
            assertLinesCount(1);
        },
    },
    /*
    * Go back to the previous page and edit the first line. We check the transaction
    * doesn't crash and the form view is correctly filled.
    */

    {
        trigger: '.o_previous_page',
    },

    {
        trigger: '.o_barcode_summary_location_dest:contains("Shelf 2")',
        run: function() {
            assertPager('1/2');
            assertPageSummary('From Shelf 1 To Shelf 2');
            assertLinesCount(1);
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(true);
            assertNextEnabled(true);
            assertNextIsHighlighted(true);
            var $line = getLine({barcode: 'product1'});
            assertLineIsHighlighted($line, false);
        },
    },

    {
        trigger: '.o_edit',
    },

    {
        trigger: '.o_form_label:contains("Product")',
        run: function() {
            assertFormLocationSrc("WH/Stock/Shelf 1");
            assertFormLocationDest("WH/Stock/Shelf 2");
            assertFormQuantity("2.000");
        },
    },

    {
        trigger: '.o_save',
    },

    /* Move 1 product2 from shelf 1 to shelf 2.
     */
    {
        trigger: '.o_add_line',
    },

    {
        extra_trigger: '.o_form_label:contains("Product")',
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text product2',
    },

    {
        trigger: ".ui-menu-item > a:contains('product2')",
    },

    {
        trigger: ".o_field_widget[name=location_id] input",
        run: 'text Shelf 1',
    },

    {
        trigger: ".ui-menu-item > a:contains('Shelf 1')",
    },

    {
        trigger: ".o_field_widget[name=location_dest_id] input",
        run: 'text Shelf 2',
    },

    {
        trigger: ".ui-menu-item > a:contains('Shelf 2')",
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_barcode_summary_location_dest:contains("Shelf 2")',
        run: function() {
            assertLinesCount(2);
        },
    },
    /* on this page, scan a product and then edit it through with the form view without explicitly saving it first.
    */
    {
        trigger: '.o_next_page',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_edit',
    },

    {
        trigger: '.o_form_label:contains("Product")',
    },

    {
        trigger :'.o_save',
    },

    {
        trigger: '.o_validate_page',
    }
]);

tour.register('test_internal_picking_reserved_1', {test: true}, [
    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 2');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(true);
            assertNextEnabled(true);
            assertNextIsHighlighted(false);
            assertLinesCount(2);
            assertScanMessage('scan_src');
            assertLocationHighlight(false);
            assertDestinationLocationHighlight(false);
            assertPager('1/2');
            assertValidateVisible(false);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(false);
            var $lineproduct1 = getLine({barcode: 'product1'});
            assertLineIsHighlighted($lineproduct1, false);
            var $lineproduct2 = getLine({barcode: 'product2'});
            assertLineIsHighlighted($lineproduct2, false);
        }
    },

    /* We first move a product1 fro shef3 to shelf2.
     */
    {
        trigger: '.barcode_client_action',
        run: 'scan shelf3'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 3 To Stock');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(0);
            assertScanMessage('scan_products');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(false);
            assertPager('3/3');
            assertValidateVisible(true);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(false);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 3 To Stock');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(1);
            assertScanMessage('scan_more_dest');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(false);
            assertPager('3/3');
            assertValidateVisible(true);
            assertValidateIsHighlighted(true);
            assertValidateEnabled(true);
            var $lineproduct1 = getLine({barcode: 'product1'});
            assertLineIsHighlighted($lineproduct1, true);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-02-00'
    },

    {
        trigger: '.o_barcode_summary_location_dest:contains("Shelf 2")',
        run: function() {
            assertPageSummary('From Shelf 3 To Shelf 2');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(1);
            assertScanMessage('scan_src');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(true);
            assertPager('3/3');
            assertValidateVisible(true);
            assertValidateIsHighlighted(true);
            assertValidateEnabled(true);
            var $lineproduct1 = getLine({barcode: 'product1'});
            assertLineIsHighlighted($lineproduct1, false);
        }
    },

    /* Hit two times previous to get to the shelf1 to fhel2 page.
     */
    {
        'trigger': '.o_previous_page',
    },

    {
        'trigger': '.o_previous_page',
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 2');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(true);
            assertNextEnabled(true);
            assertNextIsHighlighted(false);
            assertLinesCount(2);
            assertScanMessage('scan_src');
            assertLocationHighlight(false);
            assertDestinationLocationHighlight(false);
            assertPager('1/3');
            assertValidateVisible(false);
            assertValidateIsHighlighted(false);
            assertValidateVisible(false);
            var $lineproduct1 = getLine({barcode: 'product1'});
            assertLineIsHighlighted($lineproduct1, false);
            var $lineproduct2 = getLine({barcode: 'product2'});
            assertLineIsHighlighted($lineproduct2, false);
        }
    },

    /* Process the reservation.
     */
    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 2');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(true);
            assertNextEnabled(true);
            assertNextIsHighlighted(false);
            assertLinesCount(2);
            assertScanMessage('scan_products');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(false);
            assertPager('1/3');
            assertValidateVisible(false);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(false);
            var $lineproduct1 = getLine({barcode: 'product1'});
            assertLineIsHighlighted($lineproduct1, false);
            var $lineproduct2 = getLine({barcode: 'product2'});
            assertLineIsHighlighted($lineproduct2, false);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 2');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(true);
            assertNextEnabled(true);
            assertNextIsHighlighted(false);
            assertLinesCount(2);
            assertScanMessage('scan_more_dest');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(false);
            assertPager('1/3');
            assertValidateVisible(false);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(false);
            var $lineproduct1 = getLine({barcode: 'product1'});
            assertLineIsHighlighted($lineproduct1, true);
            var $lineproduct2 = getLine({barcode: 'product2'});
            assertLineIsHighlighted($lineproduct2, false);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 2');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(true);
            assertNextEnabled(true);
            assertNextIsHighlighted(true);
            assertLinesCount(2);
            assertScanMessage('scan_more_dest');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(false);
            assertPager('1/3');
            assertValidateVisible(false);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(false);
            var $lineproduct1 = getLine({barcode: 'product1'});
            assertLineIsHighlighted($lineproduct1, false);
            var $lineproduct2 = getLine({barcode: 'product2'});
            assertLineIsHighlighted($lineproduct2, true);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-02-00'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Shelf 1 To Shelf 2');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(true);
            assertNextEnabled(true);
            assertNextIsHighlighted(true);
            assertLinesCount(2);
            assertScanMessage('scan_src');
            assertLocationHighlight(true);
            assertDestinationLocationHighlight(true);
            assertPager('1/3');
            assertValidateVisible(false);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(false);

            $('.line .fa-cubes').parent().each(function() {
                var qty = $(this).text().trim();
                if (qty !== '1 / 1') {
                    fail();
                }
            });

            var $lineproduct1 = getLine({barcode: 'product1'});
            assertLineIsHighlighted($lineproduct1, false);
            var $lineproduct2 = getLine({barcode: 'product2'});
            assertLineIsHighlighted($lineproduct2, false);
        }
    },

    /* Hit next. The write should happen.
     */
    {
        'trigger': '.o_next_page',
    },

    {
        trigger: '.o_barcode_summary_location_dest:contains("Shelf 4")',
        run: function() {
            assertPageSummary('From Shelf 3 To Shelf 4');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(true);
            assertNextEnabled(true);
            assertNextIsHighlighted(false);
            assertLinesCount(1);
            assertScanMessage('scan_src');
            assertLocationHighlight(false);
            assertDestinationLocationHighlight(false);
            assertPager('2/3');
            assertValidateVisible(false);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(false);

            $('.line .fa-cubes').parent().each(function() {
                var qty = $(this).text().trim();
                if (qty !== '0 / 1') {
                    fail();
                }
            });

            var $line = getLine({barcode: 'product2'});
            assertLineIsHighlighted($line, false);
        }
    },
]);

tour.register('test_receipt_reserved_1', {test: true}, [
    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary(' To Stock');
            assertPreviousVisible(true);
            assertPreviousEnabled(false);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(2);
            assertScanMessage('scan_products');
            assertLocationHighlight(false);
            assertDestinationLocationHighlight(false);
            assertPager('1/1');
            assertValidateVisible(true);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(true);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_barcode_summary_location_dest:contains("Shelf 1")',
        run: function() {
            assertPageSummary(' To Shelf 1');
            assertPreviousVisible(true);
            assertPreviousEnabled(false);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(2);
            assertScanMessage('scan_products');
            // not relevant in receipt mode
            // assertLocationHighlight(false);
            assertDestinationLocationHighlight(true);
            assertPager('1/1');
            assertValidateVisible(true);
            assertValidateIsHighlighted(true);
            assertValidateEnabled(true);

            $('.line .fa-cubes').parent().each(function() {
                var qty = $(this).text().trim();
                if (qty !== '1 / 4') {
                    fail();
                }
            });
        }
    },
]);

tour.register('test_delivery_reserved_1', {test: true}, [
    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Stock ');
            assertPreviousVisible(true);
            assertPreviousEnabled(false);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(2);
            assertScanMessage('scan_src');
            assertLocationHighlight(false);
            // not relevant in delivery mode
            // assertDestinationLocationHighlight(false);
            assertPager('1/1');
            assertValidateVisible(true);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(true);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-00-00'
    },

    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary('From Stock ');
            assertPreviousVisible(true);
            assertPreviousEnabled(false);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(2);
            assertScanMessage('scan_products');
            assertLocationHighlight(true);
            // not relevant in delivery mode
            // assertDestinationLocationHighlight(false);
            assertPager('1/1');
            assertValidateVisible(true);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(true);
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_barcode_summary_location_src:contains("Shelf 1")',
        run: function() {
            assertPageSummary('From Shelf 1 ');
            assertPreviousVisible(true);
            assertPreviousEnabled(true);
            assertNextVisible(false);
            assertNextEnabled(false);
            assertNextIsHighlighted(false);
            assertLinesCount(0);
            assertScanMessage('scan_products');
            assertLocationHighlight(true);
            // not relevant in delivery mode
            // assertDestinationLocationHighlight(false);
            assertPager('2/2');
            assertValidateVisible(true);
            assertValidateIsHighlighted(false);
            assertValidateEnabled(false);
        }
    },
]);

tour.register('test_receipt_from_scratch_with_lots_1', {test: true}, [
    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary(' To Stock');
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan productserial1'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-00-00'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan productserial1'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_barcode_summary_location_dest:contains("Shelf 1")',
        run: function() {
            assertPageSummary(' To Shelf 1');
            assertPreviousVisible(true);
        }
    },
]);

tour.register('test_receipt_from_scratch_with_lots_2', {test: true}, [
    {
        trigger: '.barcode_client_action',
        run: function() {
            assertPageSummary(' To Stock');
        }
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan productlot1'
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_barcode_summary_location_dest:contains("Shelf 1")',
        run: function() {
            assertPageSummary(' To Shelf 1');
            assertPreviousVisible(true);
        }
    },
]);

tour.register('test_delivery_from_scratch_with_lots_1', {test: true}, [

    {
        trigger: '.barcode_client_action',
        run: 'scan productlot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot2',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_form_label:contains("Product")',
    },

]);

tour.register('test_delivery_from_scratch_with_sn_1', {test: true}, [
    /* scan a product tracked by serial number. Then scan 4 a its serial numbers.
    */
    {
        trigger: '.barcode_client_action',
        run: 'scan productserial1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan sn1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan sn2',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan sn3',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan sn4',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_form_label:contains("Product")',
    },

]);
tour.register('test_delivery_reserved_lots_1', {test: true}, [

    {
        trigger: '.barcode_client_action',
        run: 'scan productlot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot2',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_form_label:contains("Product")',
    },

]);

tour.register('test_delivery_reserved_with_sn_1', {test: true}, [
    /* scan a product tracked by serial number. Then scan 4 a its serial numbers.
    */
    {
        trigger: '.barcode_client_action',
        run: 'scan productserial1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan sn3',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan sn1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan sn4',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan sn2',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_form_label:contains("Product")',
    },

]);

tour.register('test_receipt_reserved_lots_multiloc_1', {test: true}, [
    /* Receipt of a product tracked by lots. Open an existing picking with 4
    * units initial demands. Scan 2 units in lot1 in location Stock. Then scan
    * 2 unit in lot2 in location shelf 2
    */

    {
        trigger: '.barcode_client_action',
        run: 'scan productlot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-02-00',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan productlot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-01-00',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_form_label:contains("Product")',
    },

]);


tour.register('test_inventory_adjustment', {test: true}, [

    {
        trigger: '.button_inventory',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1',
    },
    
    {
        trigger: '.barcode_client_action',
        run: 'scan product1',
    },
    
    {
        trigger: '.o_edit',
    },
    
    {
        trigger: '.o_form_label:contains("Product")',
        run: function () {
            assertInventoryFormQuantity('2.000');
        }
    },
    
    {
        trigger :'.o_save',
    },

    {
        trigger: '.o_add_line',
    },

    {
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text product2',
    },

    {
        trigger: ".ui-menu-item > a:contains('product2')",
    },

    {
        trigger: "input.o_field_widget[name=product_qty]",
        run: 'text 2',
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_form_label:contains("Product")',
    },

]);

tour.register('test_inventory_adjustment_mutli_location', {test: true}, [

    {
        trigger: '.button_inventory',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-00-00'
    },

    {
        trigger: '.o_barcode_summary_location_src:contains("Stock")',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1',
    },
    
    {
        trigger: '.barcode_client_action',
        run: 'scan product1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product2',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_barcode_summary_location_src:contains("Shelf 1")',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product2',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan LOC-01-02-00'
    },

    {
        trigger: '.o_barcode_summary_location_src:contains("Shelf 2")',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan product1',
    },

    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_form_label:contains("Product")',
    },

]);

tour.register('test_inventory_adjustment_tracked_product', {test: true}, [

    {
        trigger: '.button_inventory',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan productlot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan productserial1',
    },
    
    {
        trigger: '.barcode_client_action',
        run: 'scan serial1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan serial2',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan productlot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan productserial1',
    },

    {
        trigger: '.barcode_client_action',
        run: 'scan serial3',
    },

    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_form_label:contains("Product")',
    },
]);

});
