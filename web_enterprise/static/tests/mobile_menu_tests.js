odoo.define('web_enterprise.mobile_menu_tests', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var ConCurrency = require('web.concurrency');
var Menu = require('web_enterprise.Menu');
var testUtils = require('web.test_utils');

QUnit.module('web_enterprise mobile_menu_tests', {
    beforeEach: function () {
        this.data = {
            all_menu_ids: [1, 2, 3, 4, 5],
            'name': "root",
            children: [{
                id: 1,
                name: "Discuss",
                children: [],
             }, {
                 id: 2,
                 name: "Calendar",
                 children: []
             }, {
                id: 3,
                name: "Contacts",
                children: [
                    // 0th Object
                     {
                        id: 4,
                        name: "Contacts",
                        children: [],
                        parent_id: [{0: 3}, {1: "Contacts"}],
                     },
                     // 1st Object
                     {
                        id: 5,
                        name: "Configuration",
                        parent_id: [{0: 3}, {1: "Contacts"}],
                        children: [
                            // 1 Level - 0th Object
                            {
                                id: 6,
                                name: "Contact Tags",
                                children: [],
                                parent_id: [{0: 5}, {1: "Contacts/Configuration"}],
                            },
                            // 1 Level - 1st Object
                            {
                                id: 7,
                                name: "Contact Titles",
                                children: [],
                                parent_id: [{0: 5}, {1: "Contacts/Configuration"}],
                            },
                            // 1 Level - 2nd Object
                            {
                                id: 8,
                                name: "Activity",
                                children: [],
                                parent_id: [{0: 5}, {1: "Contacts/Configuration"}],
                            },
                            // 1 Level - 3rd Object
                            {
                                id: 9,
                                name: "Localization",
                                parent_id: [{0: 5}, {1: "Contacts/Configuration"}],
                                children:[
                                    // 2nd Level - 0th Object
                                    {
                                        id: 10,
                                        name: "Countries",
                                        children: [],
                                        parent_id: [{0: 9}, {1: "Contacts/Configuration/Localization"}],
                                    },
                                    // 2nd Level - 1st Object
                                    {
                                        id: 11,
                                        name: "Fed. States",
                                        children: [],
                                        parent_id: [{0: 9}, {1: "Contacts/Configuration/Localization"}],
                                    },
                                    // 2nd Level - 2nd Object
                                    {
                                        id: 12,
                                        name: "Country Group",
                                        children: [],
                                        parent_id: [{0: 9}, {1: "Contacts/Configuration/Localization"}],
                                    }
                                ]
                            },
                            // 1 Level - 4th Object
                            {
                                id: 13,
                                name: "Bank Accounts",
                                parent_id: [{0: 5}, {1: "Contacts/Configuration"}],
                                children:[
                                    // 2nd Level - 0th Object
                                    {
                                        id: 14,
                                        name: "Banks",
                                        children: [],
                                        parent_id: [{0: 13}, {1: "Contacts/Configuration/Bank Accounts"}],
                                    },
                                    // 2nd Level - 1st Object
                                    {
                                        id: 288,
                                        name: "Bank Accounts",
                                        children: [],
                                        parent_id: [{0: 13}, {1: "Contacts/Configuration/Bank Accounts"}],
                                    }
                                ]
                            }
                        ]
                     }
                ]
           }],
        };
    }
}, function () {

    QUnit.module('mobile_menu_tests');

    QUnit.test('Mobile Menu on Home Screen', function (assert) {
        assert.expect(1);

        function createParent (params) {
            var actionManager = new ActionManager();
            testUtils.addMockEnvironment(actionManager, params);
            return actionManager;
        }

        var parent = createParent({
            data: {},
            config: {isMobile: true}
        });

        var mobileMenu = new Menu(parent, this.data);
        testUtils.addMockEnvironment(mobileMenu, {
            mockRPC: function (route, args) {
                return $.when([]);
            },
        });
        mobileMenu.appendTo($('#qunit-fixture'));

        mobileMenu.$('.o_mobile_menu_toggle').click();
        assert.ok(!mobileMenu.$(".o_mobile_menu_container").hasClass('o_hidden'), "Burger menu should be opened on button click");
        mobileMenu.$('.o_mobile_menu_close').click();
        mobileMenu.destroy();
    });

    QUnit.test('Burger Menu on any Module', function (assert) {
        assert.expect(5);
        function createParent (params) {
            var actionManager = new ActionManager();
            testUtils.addMockEnvironment(actionManager, params);
            return actionManager;
        }

        var parent = createParent({
            data: {},
            config: {isMobile: true}
        });

        var mobileMenu = new Menu(parent, this.data);
        testUtils.addMockEnvironment(mobileMenu, {
            mockRPC: function (route, args) {
                return $.when([]);
            },
        });
        mobileMenu.appendTo($('#qunit-fixture'));
        mobileMenu.change_menu_section(3);
        mobileMenu.toggle_mode(false);

        mobileMenu.$('.o_mobile_menu_toggle').click();
        assert.ok(!mobileMenu.$(".o_mobile_menu_container").hasClass('o_hidden'), "Burger menu should be opened on button click");
        mobileMenu.$('.o_mobile_menu_user_menu').click();
        assert.ok(!mobileMenu.$(".o_mobile_menu_content").hasClass('o_mobile_menu_darken'), "Toggle to usermenu on header click");
        mobileMenu.$('.o_mobile_menu_user_menu').click();
        assert.ok(mobileMenu.$(".o_mobile_menu_content").hasClass('o_mobile_menu_darken'), "Toggle back to main sales menu on header click");
        mobileMenu.$('.o_burger_menu_root > .o_burger_menu_section').click();
        assert.notEqual(mobileMenu.$('.o_mobile_menu_section_container > li').length, 0, "Should open second level menu");
        mobileMenu.$('.o_mobile_menu_section_container > .o_burger_menu_section:first()').click();
        assert.notEqual(mobileMenu.$('.o_mobile_menu_section_container > li').length, 0, "Shoule open third level menu");
        mobileMenu.$('.o_mobile_menu_close').click();
        mobileMenu.destroy();
    });
});
});
