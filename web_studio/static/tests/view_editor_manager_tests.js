odoo.define('web_studio.ViewEditorManager_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var testUtils = require("web.test_utils");
var Widget = require('web.Widget');

var createViewEditorManager = function (arch, params) {
    var $target = $('#qunit-fixture');

    params = params || {};
    var modelName = 'coucou';
    var widget = new Widget();
    var data = params.data || {
        coucou: {
            fields: {
                display_name: {
                    string: "Display Name",
                    type: "char"
                },
            },
        },
    };
    var mockServer = testUtils.addMockEnvironment(widget, {
        data: data,
        mockRPC: function(route, args) {
            if (route === '/web_studio/get_default_value') {
                return $.when({});
            }
            if (route === '/web_studio/get_email_alias') {
                return $.when({email_alias: 'coucou'});
            }
            return this._super(route, args);
        },
    });
    var fieldsView = mockServer.fieldsViewGet(arch, modelName);
    var env = {
        modelName: modelName,
        ids: undefined,
        currentId: undefined,
        domain: undefined,
        context: {},
        groupBy: [],
    };
    // var options = {
    //     ids: [1],
    //     res_id: 1,
    //     studioViewArch: "<data/>",
    //     studioViewID: 1,
    // };
    var vem = new ViewEditorManager(widget, {
        fields_view: fieldsView,
        view_env: env,

    });
    vem.appendTo($target);
    return vem;
};

var ViewEditorManager = require('web_studio.ViewEditorManager');

QUnit.module('Studio', {}, function () {

    QUnit.module('ViewEditorManager');

    QUnit.test('list editor sidebar', function(assert) {
        assert.expect(5);

        var arch = "<tree/>";
        var vem = createViewEditorManager(arch);

        assert.strictEqual(vem.$('.o_web_studio_sidebar').length, 1,
            "there should be a sidebar");
        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_new').hasClass('active'),
            "the Add tab should be active in list view");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('.o_web_studio_field_type_container').length, 2,
            "there should be two sections in Add (new & existing fields");

        vem.$('.o_web_studio_sidebar').find('.o_web_studio_view').click();

        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_view').hasClass('active'),
            "the View tab should now be active");
        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties').hasClass('disabled'),
            "the Properties tab should now be disabled");

        vem.destroy();
    });

    QUnit.test('empty list editor', function(assert) {
        assert.expect(5);

        var arch = "<tree/>";
        var vem = createViewEditorManager(arch);

        assert.strictEqual(vem.view_type, 'list',
            "view type should be list");
        assert.strictEqual(vem.$('.o_web_studio_list_view_editor').length, 1,
            "there should be a list editor");
        assert.strictEqual(vem.$('.o_web_studio_list_view_editor table thead th.o_web_studio_hook').length, 1,
            "there should be one hook");
        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 0,
            "there should be no node");
        assert.strictEqual(vem.$('.o_web_studio_sidebar .o_web_studio_existing_fields').children().length, 3,
            "there should be one available field (id, name, display_name)");

        vem.destroy();
    });

    QUnit.test('list editor', function(assert) {
        assert.expect(3);

        var arch =
            "<tree>" +
                "<field name='display_name'/>" +
            "</tree>";
        var vem = createViewEditorManager(arch);

        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 1,
            "there should be one node");
        assert.strictEqual(vem.$('table thead th.o_web_studio_hook').length, 2,
            "there should be two hooks (before & after the field)");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('.o_web_studio_existing_fields').children().length, 2,
            "there should be two available fields (id, name)");

        vem.destroy();
    });

    QUnit.test('invisible list editor', function(assert) {
        assert.expect(4);

        var arch =
            "<tree>" +
                "<field name='display_name' invisible='1'/>" +
            "</tree>";
        var vem = createViewEditorManager(arch);

        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 0,
            "there should be no node");
        assert.strictEqual(vem.$('table thead th.o_web_studio_hook').length, 1,
            "there should be one hook");

        // click on show invisible
        vem.$('.o_web_studio_sidebar').find('.o_web_studio_view').click();
        vem.$('.o_web_studio_sidebar').find('input#show_invisible').click();

        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 1,
            "there should be one node (the invisible one)");
        assert.strictEqual(vem.$('table thead th.o_web_studio_hook').length, 2,
            "there should be two hooks (before & after the field)");

        vem.destroy();
    });

    QUnit.test('list editor field', function(assert) {
        assert.expect(5);

        var arch =
            "<tree>" +
                "<field name='display_name'/>" +
            "</tree>";
        var vem = createViewEditorManager(arch);

        // click on the field
        vem.$('.o_web_studio_list_view_editor [data-node-id]').click();

        assert.ok(vem.$('.o_web_studio_list_view_editor [data-node-id]').hasClass('o_clicked'),
            "the column should have the clicked style");

        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties').hasClass('active'),
            "the Properties tab should now be active");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field').length, 1,
            "the sidebar should now display the field properties");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('input[name="string"]').val(), "Display Name",
            "the label in sidebar should be Display Name");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="widget"]').val(), "",
            "the widget in sidebar should be emtpy");

        vem.destroy();
    });

    QUnit.test('empty form editor', function(assert) {
        assert.expect(4);

        var arch = "<form/>";
        var vem = createViewEditorManager(arch);

        assert.strictEqual(vem.view_type, 'form',
            "view type should be form");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor').length, 1,
            "there should be a form editor");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor [data-node-id]').length, 0,
            "there should be no node");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_web_studio_hook').length, 0,
            "there should be no hook");

        vem.destroy();
    });

    QUnit.test('form editor', function(assert) {
        assert.expect(6);

        var arch =
            "<form>" +
                "<sheet>" +
                    "<field name='display_name'/>" +
                "</sheet>" +
            "</form>";
        var vem = createViewEditorManager(arch);

        assert.strictEqual(vem.$('.o_web_studio_form_view_editor [data-node-id]').length, 1,
            "there should be one node");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_web_studio_hook').length, 1,
            "there should be one hook");

        vem.$('.o_web_studio_form_view_editor [data-node-id]').click();

        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties').hasClass('active'),
            "the Properties tab should now be active");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field').length, 1,
            "the sidebar should now display the field properties");
        assert.ok(vem.$('.o_web_studio_form_view_editor [data-node-id]').hasClass('o_clicked'),
            "the column should have the clicked style");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="widget"]').val(), "",
            "the widget in sidebar should be empty");

        vem.destroy();
    });

    QUnit.test('invisible form editor', function(assert) {
        assert.expect(6);

        var arch =
            "<form>" +
                "<sheet>" +
                    "<field name='display_name' invisible='1'/>" +
                "</sheet>" +
            "</form>";
        var vem = createViewEditorManager(arch);

        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_form_invisible[data-node-id]').length, 1,
            "there should be one invisible node");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor [data-node-id]:not(.o_form_invisible)').length, 0,
            "there should be no visible node");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_web_studio_hook').length, 1,
            "there should be one hook");

        // click on show invisible
        vem.$('.o_web_studio_sidebar').find('.o_web_studio_view').click();
        vem.$('.o_web_studio_sidebar').find('input#show_invisible').click();

        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_web_studio_show_invisible[data-node-id]').length, 1,
            "there should be one visible node (the invisible one)");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_form_invisible[data-node-id]').length, 0,
            "there should be no invisible node");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_web_studio_hook').length, 1,
            "there should be one hook");

        vem.destroy();
    });

    QUnit.test('form editor - chatter edition', function(assert) {
        assert.expect(5);

        var arch =
            "<form>" +
                "<sheet>" +
                    "<field name='display_name'/>" +
                "</sheet>" +
                "<div class='oe_chatter'/>" +
            "</form>";

        var vem = createViewEditorManager(arch);

        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .oe_chatter[data-node-id]').length, 1,
            "there should be a chatter node");

        // click on the chatter
        vem.$('.o_web_studio_form_view_editor .oe_chatter[data-node-id]').click();

        assert.ok(vem.$('.o_web_studio_sidebar .o_web_studio_properties').hasClass('active'),
            "the Properties tab should now be active");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_chatter').length, 1,
            "the sidebar should now display the chatter properties");
        assert.ok(vem.$('.o_web_studio_form_view_editor .oe_chatter[data-node-id]').hasClass('o_clicked'),
            "the chatter should have the clicked style");
        assert.strictEqual(vem.$('.o_web_studio_sidebar input[name="email_alias"]').val(), "coucou",
            "the email alias in sidebar should be fetched");

        vem.destroy();
    });

    QUnit.test('empty kanban editor', function(assert) {
        assert.expect(4);

        var arch =
            "<kanban>" +
                "<templates><t t-name='kanban-box'/></templates>" +
            "</kanban>";
        var vem = createViewEditorManager(arch);

        assert.strictEqual(vem.view_type, 'kanban',
            "view type should be kanban");
        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor').length, 1,
            "there should be a kanban editor");
        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor [data-node-id]').length, 0,
            "there should be no node");
        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor .o_web_studio_hook').length, 0,
            "there should be no hook");

        vem.destroy();
    });

    QUnit.test('kanban editor', function(assert) {
        assert.expect(13);

        var arch =
            "<kanban>" +
                "<templates>" +
                    "<t t-name='kanban-box'>" +
                        "<div class='o_kanban_record'>" +
                            "<field name='display_name'/>" +
                        "</div>" +
                    "</t>" +
                "</templates>" +
            "</kanban>";
        var vem = createViewEditorManager(arch);

        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor [data-node-id]').length, 1,
            "there should be one node");
        assert.ok(vem.$('.o_web_studio_kanban_view_editor [data-node-id]').hasClass('o_web_studio_widget_empty'),
            "the empty node should have the empty class");
        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor .o_web_studio_hook').length, 1,
            "there should be one hook");
        assert.strictEqual(vem.$('.o_kanban_record .o_web_studio_add_kanban_tags').length, 1,
            "there should be the hook for tags");
        assert.strictEqual(vem.$('.o_kanban_record .o_web_studio_add_dropdown').length, 1,
            "there should be the hook for dropdown");
        assert.strictEqual(vem.$('.o_kanban_record .o_web_studio_add_priority').length, 1,
            "there should be the hook for priority");
        assert.strictEqual(vem.$('.o_kanban_record .o_web_studio_add_kanban_image').length, 1,
            "there should be the hook for image");

        vem.$('.o_web_studio_kanban_view_editor [data-node-id]').click();

        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties').hasClass('active'),
            "the Properties tab should now be active");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field').length, 1,
            "the sidebar should now display the field properties");
        assert.ok(vem.$('.o_web_studio_kanban_view_editor [data-node-id]').hasClass('o_clicked'),
            "the field should have the clicked style");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="widget"]').val(), "",
            "the widget in sidebar should be empty");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="display"]').val(), "false",
            "the display attribute should be Default");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('input[name="string"]').val(), "Display Name",
            "the field should have the label Display Name in the sidebar");

        vem.destroy();
    });

    QUnit.test('empty search editor', function(assert) {
        assert.expect(6);

        var arch = "<search/>";
        var vem = createViewEditorManager(arch);

        assert.strictEqual(vem.view_type, 'search',
            "view type should be search");
        assert.strictEqual(vem.$('.o_web_studio_search_view_editor').length, 1,
            "there should be a search editor");
        assert.strictEqual(vem.$('.o_web_studio_search_autocompletion_fields.table tbody tr.o_web_studio_hook').length, 1,
            "there should be one hook in the autocompletion fields");
        assert.strictEqual(vem.$('.o_web_studio_search_filters.table tbody tr.o_web_studio_hook').length, 1,
            "there should be one hook in the filters");
        assert.strictEqual(vem.$('.o_web_studio_search_group_by.table tbody tr.o_web_studio_hook').length, 1,
            "there should be one hook in the group by");
        assert.strictEqual(vem.$('.o_web_studio_search_view_editor [data-node-id]').length, 0,
            "there should be no node");
        vem.destroy();
    });

    QUnit.test('search editor', function(assert) {
        assert.expect(9);

        var arch =
            "<search>" +
                "<field name='display_name'/>" +
                "<filter string='My Name' " +
                    "name='my_name' " +
                    "domain='[(\"display_name\",\"=\",coucou)]'" +
                "/>" +
                "<filter string='My Name2' " +
                    "name='my_name2' " +
                    "domain='[(\"display_name\",\"=\",coucou2)]'" +
                "/>" +
                "<group expand='0' string='Group By'>" +
                    "<filter name='groupby_display_name' " +
                    "domain='[]' context=\"{'group_by':'display_name'}\"/>" +
                "</group>" +
            "</search>";
        var vem = createViewEditorManager(arch);

        assert.strictEqual(vem.view_type, 'search',
            "view type should be search");
        assert.strictEqual(vem.$('.o_web_studio_search_view_editor').length, 1,
            "there should be a search editor");
        assert.strictEqual(vem.$('.o_web_studio_search_autocompletion_fields.table tbody tr.o_web_studio_hook').length, 2,
            "there should be two hooks in the autocompletion fields");
        assert.strictEqual(vem.$('.o_web_studio_search_filters.table tbody tr.o_web_studio_hook').length, 3,
            "there should be three hook in the filters");
        assert.strictEqual(vem.$('.o_web_studio_search_group_by.table tbody tr.o_web_studio_hook').length, 2,
            "there should be two hooks in the group by");
        assert.strictEqual(vem.$('.o_web_studio_search_autocompletion_fields.table [data-node-id]').length, 1,
            "there should be 1 node in the autocompletion fields");
        assert.strictEqual(vem.$('.o_web_studio_search_filters.table [data-node-id]').length, 2,
            "there should be 2 nodes in the filters");
        assert.strictEqual(vem.$('.o_web_studio_search_group_by.table [data-node-id]').length, 1,
            "there should be 1 nodes in the group by");
        assert.strictEqual(vem.$('.o_web_studio_search_view_editor [data-node-id]').length, 4,
            "there should be 4 nodes");

        vem.destroy();
    });

    QUnit.test('empty pivot editor', function(assert) {
        assert.expect(3);

        var arch = "<pivot/>";
        var vem = createViewEditorManager(arch, {
            data: {
                coucou: {
                    fields: {
                        display_name: {
                            string: "Display Name",
                            type: "char",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: 'coucou',
                        }
                    ],
                },
            },
        });

        assert.strictEqual(vem.view_type, 'pivot',
            "view type should be pivot");
        assert.strictEqual(vem.$('.o_web_studio_view_renderer .o_pivot').length, 1,
            "there should be a pivot renderer");
        assert.strictEqual(vem.$('.o_web_studio_view_renderer > .o_pivot > table').length, 1,
            "the table should be the direct child of pivot");

        vem.destroy();
    });

    QUnit.test('empty graph editor', function(assert) {
        var done = assert.async();
        assert.expect(3);

        var arch = "<graph/>";
        var vem = createViewEditorManager(arch, {
            data: {
                coucou: {
                    fields: {
                        display_name: {
                            string: "Display Name",
                            type: "char",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: 'coucou',
                        }
                    ],
                },
            },
        });

        assert.strictEqual(vem.view_type, 'graph',
            "view type should be graph");
        return concurrency.delay(0).then(function () {
            assert.strictEqual(vem.$('.o_web_studio_view_renderer .o_graph').length, 1,
                "there should be a graph renderer");
            assert.strictEqual(vem.$('.o_web_studio_view_renderer > .o_graph > .o_graph_svg_container > svg').length, 1,
                "the graph should be the direct child of its container");
            vem.destroy();
            done();
        });

    });
});

});
