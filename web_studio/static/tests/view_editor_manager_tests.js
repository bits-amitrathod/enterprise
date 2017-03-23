odoo.define('web_studio.ViewEditorManager_tests', function (require) {
"use strict";

var testUtils = require("web.test_utils");
var Widget = require('web.Widget');

var createViewEditorManager = function (arch) {
    var $target = $('#qunit-fixture');

    var modelName = 'coucou';
    var widget = new Widget();
    var data = {
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
        assert.expect(0);

        var arch =
            "<kanban>" +
                "<templates>" +
                    "<t t-name='kanban-box'>" +
                        "<div>" +
                            "<field name='display_name'/>" +
                        "</div>" +
                    "</t>" +
                "</templates>" +
            "</kanban>";
        var vem = createViewEditorManager(arch);

        vem.destroy();
    });
});

});
