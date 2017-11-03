odoo.define('web_enterprise.app_switcher_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var Widget = require('web.Widget');
var AppSwitcher = require('web_enterprise.AppSwitcher');

QUnit.module('web_enterprise', {
    beforeEach: function () {
        this.data = {
            all_menu_ids: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            name: "root",
            children: [{
                id: 1,
                action: ' ',
                name: "Discuss",
                children: [],
             }, {
                 id: 2,
                 action: ' ',
                 name: "Calendar",
                 children: []
             }, {
                id: 3,
                action: ' ',
                name: "Contacts",
                children: [{
                    id: 4,
                    action: ' ',
                    name: "Contacts",
                    children: [],
                }, {
                    id: 5,
                    action: ' ',
                    name: "Configuration",
                    children: [{
                        id: 6,
                        action: ' ',
                        name: "Contact Tags",
                        children: [],
                    }, {
                        id: 7,
                        action: ' ',
                        name: "Contact Titles",
                        children: [],
                    }, {
                        id: 8,
                        action: ' ',
                        name: "Localization",
                        children: [{
                            id: 9,
                            action: ' ',
                            name: "Countries",
                            children: [],
                        }, {
                            id: 10,
                            action: ' ',
                            name: "Fed. States",
                            children: [],
                        }],
                    }],
                 }],
           }],
        };
    }
}, function () {

    QUnit.module('AppSwitcher');

    QUnit.test('ESC Support', function (assert) {
        assert.expect(7);

        var appSwitcherHidden = false;

        var parent = testUtils.createParent({
            intercepts: {
                hide_app_switcher: function () {
                    appSwitcherHidden = true;
                },
            },
        });

        var appSwitcher = new AppSwitcher(parent, this.data);

        appSwitcher.appendTo($('#qunit-fixture'));
        appSwitcher.on_attach_callback(); // simulate action manager attached to dom
        appSwitcher.$('input.o_menu_search_input').focus().click();

        // 1. search must be hidden by default
        assert.ok(
            appSwitcher.$('div.o_menu_search').hasClass('o_bar_hidden'),
            "search must be hidden by default");

        appSwitcher.$('input.o_menu_search_input').val("dis").trigger('input');

        // 2. search must be visible after some input
        assert.notOk(
            appSwitcher.$('div.o_menu_search').hasClass('o_bar_hidden'),
            "search must be visible after some input");

        // 3. search must contain the input text
        assert.strictEqual(
            appSwitcher.$('input.o_menu_search_input').val(),
            "dis",
            "search must contain the input text");

        var escEvent = $.Event('keydown', {
            which: $.ui.keyCode.ESCAPE,
            keyCode: $.ui.keyCode.ESCAPE,
        });

        appSwitcher.$('input.o_menu_search_input').trigger(escEvent);

        // 4. search must have no text after ESC
        assert.strictEqual(
            appSwitcher.$('input.o_menu_search_input').val(),
            "",
            "search must have no text after ESC");

        // 5. search must still become visible after clearing some non-empty text
        assert.notOk(
            appSwitcher.$('div.o_menu_search').hasClass('o_bar_hidden'),
            "search must still become visible after clearing some non-empty text");

        appSwitcher.$('input.o_menu_search_input').trigger(escEvent);

        // 6. search must become invisible after ESC on empty text
        assert.ok(
            appSwitcher.$('div.o_menu_search').hasClass('o_bar_hidden'),
            "search must become invisible after ESC on empty text");

        // 7. app switcher must be hidden after ESC on empty text
        assert.ok(
            appSwitcherHidden,
            "app switcher must be hidden after ESC on empty text");

        parent.destroy();
    });

});
});
