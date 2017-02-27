odoo.define('web_studio.ViewEditorManager', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var concurrency = require("web.concurrency");
var core = require('web.core');
var data_manager = require('web.data_manager');
var Dialog = require('web.Dialog');
var view_registry = require('web.view_registry');
var Widget = require('web.Widget');

var bus = require('web_studio.bus');
var customize = require('web_studio.customize');

var CalendarEditor = require('web_studio.CalendarEditor');
var FormEditor = require('web_studio.FormEditor');
var GanttEditor = require('web_studio.GanttEditor');
var GraphEditor = require('web_studio.GraphEditor');
var GridEditor =require('web_studio.GridEditor');
var KanbanEditor = require('web_studio.KanbanEditor');
var ListEditor = require('web_studio.ListEditor');
var PivotEditor = require('web_studio.PivotEditor');
var SearchEditor = require('web_studio.SearchEditor');

var NewButtonBoxDialog = require('web_studio.NewButtonBoxDialog');
var NewFieldDialog = require('web_studio.NewFieldDialog');
var utils = require('web_studio.utils');
var ViewEditorSidebar = require('web_studio.ViewEditorSidebar');
var XMLEditor = require('web_studio.XMLEditor');

var _t = core._t;

var Editors = {
    form: FormEditor,
    kanban: KanbanEditor,
    list: ListEditor,
    grid: GridEditor,
    pivot: PivotEditor,
    graph: GraphEditor,
    calendar: CalendarEditor,
    gantt: GanttEditor,
    search: SearchEditor,
};

function find_parent(arch, node) {
    var parent = arch;
    var result;
    _.each(parent.children, function(child) {
        if (child.attrs && child.attrs.name === node.attrs.name) {
            result = parent;
        } else {
            var res = find_parent(child, node);
            if (res) {
                result = res;
            }
        }
    });
    return result;
}

function find_parents_positions(arch, node) {
    return _find_parents_positions(arch, node, [], 1);
}

function _find_parents_positions(parent, node, positions, indice) {
    var result;
    positions.push({
        'tag': parent.tag,
        'indice': indice,
    });
    if (parent === node) {
        return positions;
    } else {
        var current_indices = {};
        _.each(parent.children, function(child) {
            // Save indice of each sibling node
            current_indices[child.tag] = current_indices[child.tag] ? current_indices[child.tag] + 1 : 1;
            var res = _find_parents_positions(child, node, positions, current_indices[child.tag]);
            if (res) {
                result = res;
            } else {
                positions.pop();
            }
        });
    }
    return result;
}

return Widget.extend({
    className: 'o_web_studio_view_editor',
    custom_events: {
        'node_clicked': 'toggle_editor_sidebar',
        'unselect_element': '_onUnselectElement',
        'view_change': 'update_view',
        'email_alias_change': 'set_email_alias',
        'default_value_change': 'set_default_value',
        'toggle_form_invisible': 'toggle_form_invisible',
        'open_xml_editor': 'open_xml_editor',
        'close_xml_editor': 'close_xml_editor',
        'save_xml_editor': 'save_xml_editor',
        'open_view_form': 'open_view_form',
        'open_defaults': 'open_defaults',
        'open_field_form': 'open_field_form',
        'drag_component' : 'show_nearest_hook',
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    init: function (parent, modelName, fieldsView, viewType, options) {
        this._super.apply(this, arguments);

        this.modelName = modelName;
        this.fieldsView = fieldsView;
        this.viewType = viewType;
        this.view_id = this.fieldsView.view_id;
        this.view_attrs = this.fieldsView.arch.attrs;
        this.mode = 'edition';  // the other mode is 'rendering' when using the XML editor
        this.editor = undefined;
        this.renderer = undefined;
        this.sidebar = undefined;
        this.operations = [];
        this.operationsUndone = [];
        this.exprAttrs = {
            'field': ['name'],
            'label': ['for'],
            'page': ['name'],
            'group': ['name'],
            'div': ['class'],
            'button': ['name'],
            'filter': ['name'],
        };
        this.ids = options.ids || [];
        this.res_id = options.res_id;
        this.chatter_allowed = options.chatter_allowed;
        this.studioViewID = options.studioViewID;
        this.studioViewArch = options.studioViewArch;

        this._apply_changes_mutex = new concurrency.Mutex();

        bus.on('undo_clicked', this, this.undo);
        bus.on('redo_clicked', this, this.redo);
    },
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            return $.when(
                self.loadSidebar(),
                self.loadView()
            ).then(function (sidebar, editor) {
                self.sidebar = sidebar;
                self.sidebar.appendTo(self.$el);

                self.editor = editor;
                var $editorFragment = $('<div>', {
                    class: 'o_web_studio_view_renderer',
                });
                self.editor.appendTo($editorFragment);
                $editorFragment.appendTo(self.$el);
            });
        });
    },
    destroy: function() {
        bus.trigger('undo_not_available');
        bus.trigger('redo_not_available');
    },
    get_fields_not_in_view: function() {
        // Remove fields that are already in the view
        var fields_not_in_view = _.omit(this.fields, Object.keys(this.fieldsView.fields));

        if (this.view_type === 'kanban') {
            // as there is no widget image in the kanban field registry in
            // the old views, we prevent to user to add a binary field in kanban
            // TODO: remove this with the new views
            fields_not_in_view = _.omit(fields_not_in_view, function(field) {
                return field.type === 'binary';
            });
        }

        // Convert dict to array
        var list = _.map(fields_not_in_view, function(dict, key) {
            return _.extend({name: key}, dict);
        });

        // Sort by field_description (alphabetically)
        return _.sortBy(list, function (field) {
            return field.string.toLowerCase();
        });
    },
    loadSidebar: function () {
        var attrs = {
            viewType: this.viewType,
            view_attrs: this.view_attrs,
            model: this.model,
            fields: this.fields,
            fields_not_in_view: this._get_fields_not_in_view(),
            fields_in_view: this.fieldsView.fields,
        };
        return new ViewEditorSidebar(this, attrs);
    },
    loadView: function () {
        var params = {
            modelName: this.modelName,
            context: {},  // TODO: no idea where to find all the params
        };
        var View = view_registry.get(this.viewType);
        this.view = new View(this.fieldsView.arch, this.fieldsView.fields, params);
        var def;
        if (this.mode === 'edition') {
            var Editor = Editors[this.viewType];
            def = this.view.createStudioEditor(this, Editor);
        } else {
            def = this.view.createStudioRenderer(this);
        }
        return def;
    },
    updateEditor: function (replace, options) {
        var self = this;
        var oldEditor;
        var renderer_scrolltop = this.$el.scrollTop();
        var local_state = this.editor ? this.editor.getLocalState() : false;

        options = _.extend({}, options, {
            chatter_allowed: this.chatter_allowed,
            show_invisible: this.sidebar.show_invisible,
            arch: this.fieldsView.arch,
        });

        oldEditor = this.editor;
        return this.loadView().then(function (editor) {
            self.editor = editor;
            var fragment = document.createDocumentFragment();
            try {
                return self.editor.appendTo(fragment).then(function () {
                    self.$('.o_web_studio_view_renderer').append(fragment);

                    oldEditor.destroy();

                    // restore previous state
                    self.$el.scrollTop(renderer_scrolltop);
                    if (local_state) {
                        self.editor.setLocalState(local_state);
                    }
                });
            } catch (e) {
                this.trigger_up('studio_error', {error: 'view_rendering'});
                this.undo(true);
            }
        });
    },
    do: function(op) {
        this.operations.push(op);
        this.operationsUndone = [];

        return this.applyChanges(false, op.type === 'replace_arch');
    },
    undo: function(forget) {
        if (!this.operations.length) {
            return;
        }
        var op = this.operations.pop();
        if (!forget) {
            this.operationsUndone.push(op);
        }

        if (op.type === 'replace_arch') {
            // as the whole arch has been replace (A -> B),
            // when undoing it, the operation (B -> A) is added and
            // removed just after.
            var undo_op = jQuery.extend(true, {}, op);
            undo_op.old_arch = op.new_arch;
            undo_op.new_arch = op.old_arch;
            this.operations.push(undo_op);
            return this.applyChanges(true, true);
        } else {
            return this.applyChanges(false, false);
        }
    },
    redo: function() {
        if (!this.operationsUndone.length) {
            return;
        }
        var op = this.operationsUndone.pop();
        this.operations.push(op);

        return this.applyChanges(false, op.type === 'replace_arch');
    },
    updateButtons: function() {
        // Undo button
        if (this.operations.length) {
            bus.trigger('undo_available');
        } else {
            bus.trigger('undo_not_available');
        }

        // Redo button
        if (this.operationsUndone.length) {
            bus.trigger('redo_available');
        } else {
            bus.trigger('redo_not_available');
        }
    },
    applyChanges: function(remove_last_op, from_xml) {
        var self = this;

        var last_op = this.operations.slice(-1)[0];

        var def;
        if (from_xml) {
            def = this._apply_changes_mutex.exec(customize.edit_view_arch.bind(
                customize,
                last_op.view_id,
                last_op.new_arch
            )).fail(function() {
                self.trigger_up('studio_error', {error: 'view_rendering'});
            });
        } else {
            def = this._apply_changes_mutex.exec(customize.edit_view.bind(
                customize,
                this.view_id,
                this.studioViewArch,
                _.filter(this.operations, function(el) {return el.type !== 'replace_arch'; })
            ));
        }

        return def.then(function (result) {
            if (!result.fieldsView) {
                self.trigger_up('studio_error', {error: 'wrong_xpath'});
                return self.undo(true).then(function () {
                    return $.Deferred().reject(); // indicate that the operation can't be applied
                });
            }
            // "/web_studio/edit_view" returns "fields" only when we created a new field.
            if (result.fields) {
                self.fields = result.fields;
            }
            self.fieldsView = data_manager._postprocess_fvg(result.fieldsView);

            // As the studio view arch is stored in this widget, if this view
            // is updated directly with the XML editor, the arch should be updated.
            // The operations may not have any sense anymore so they are dropped.
            if (from_xml && last_op.view_id === self.studioViewID) {
                self.studioViewArch = last_op.new_arch;
                self.operations = [];
                self.operationsUndone = [];
            }
            if (remove_last_op) { self.operations.pop(); }
            self.updateButtons();

            return self.updateEditor(true).then(function() {
                // fields and fieldsView has been updated.
                // So first we have to calculate which fields are in the view or not.
                // Then we want to update sidebar who displays "existing fields"
                self.sidebar.update(self.fields, self._get_fields_not_in_view(), self.fieldsView.fields, self.fieldsView.arch.attrs);
            });
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _add_element: function(type, node, xpath_info, position, tag) {
        this.do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.exprAttrs[node.tag]),
                xpath_info: xpath_info,
            },
            position: position,
            node: {
                tag: tag,
                attrs: {
                    name: 'studio_' + tag + '_' + utils.randomString(5),
                }
            },
        });
    },
    _add_button: function(data) {
        var self = this;
        var dialog = new NewButtonBoxDialog(this, this.modelName).open();
        dialog.on('saved', this, function(result) {
            var def;
            if (data.add_buttonbox) {
                this.operations.push({
                    type: 'buttonbox',
                });
            }
            $.when(def).then(function () {
                    self.do({
                    type: data.type,
                    target: {
                        tag: 'div',
                        attrs: {
                            class: 'oe_button_box',
                        }
                    },
                    position: 'inside',
                    node: {
                        tag: 'button',
                        field: result.field_id,
                        string: result.string,
                        attrs: {
                            class: 'oe_stat_button',
                            icon: result.icon,
                        }
                    },
                });
            });
        });
    },
    _add_page: function(type, node, xpath_info, position) {
        this.do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.exprAttrs[node.tag]),
                xpath_info: xpath_info,
            },
            position: position,
            node: {
                tag: 'page',
                attrs: {
                    string: 'New Page',
                    name: 'studio_page_' + utils.randomString(5),
                }
            },
        });
    },
    _add_field: function(type, field_description, node, xpath_info, position, new_attrs) {
        var self = this;
        var def_field_values;

        // The field doesn't exist: field_description is the definition of the new field.
        // No need to have field_description of an existing field
        if (field_description) {
            // "extend" avoids having the same reference in "this.operations"
            // We can thus modify it without editing previous existing operations
            field_description = _.extend({}, field_description, {
                name: 'x_studio_field_' + utils.randomString(5),
                model_name: this.model,
            });
            // Fields with requirements
            // Open Dialog to precise the required fields for this field.
            if (_.contains(['selection', 'one2many', 'many2one', 'many2many', 'related'], field_description.ttype)) {
                def_field_values = $.Deferred();
                var dialog = new NewFieldDialog(this, this.modelName, field_description.ttype, this.fields).open();
                dialog.on('field_default_values_saved', this, function(values) {
                    def_field_values.resolve(values);
                    dialog.close();
                });
                dialog.on('closed', this, function() {
                    def_field_values.reject();
                });
            }
            if (field_description.ttype === 'monetary') {
                def_field_values = $.Deferred();
                // Detect currency_id on the current model
                new BasicModel("ir.model.fields").call("search", [[
                    ['name', '=', 'currency_id'],
                    ['model', '=', this.modelName],
                    ['relation', '=', 'res.currency'],
                ]]).then(function(data) {
                    if (!data.length) {
                        Dialog.alert(self, _t('This field type cannot be dropped on this model.'));
                        def_field_values.reject();
                    } else {
                        def_field_values.resolve();
                    }
                });
            }
        }
        // When the field values is selected, close the dialog and update the view
        $.when(def_field_values).then(function(values) {
            self.do({
                type: type,
                target: {
                    tag: node.tag,
                    attrs: _.pick(node.attrs, self.exprAttrs[node.tag]),
                    xpath_info: xpath_info,
                },
                position: position,
                node: {
                    tag: 'field',
                    attrs: new_attrs,
                    field_description: _.extend(field_description, values),
                },
            });
        }).fail(function() {
            self.updateEditor(true);
        });
    },
    _add_chatter: function(data) {
        this.do({
            type: 'chatter',
            model: this.modelName,
            remove_message_ids: data.remove_message_ids,
            remove_follower_ids: data.remove_follower_ids,
        });
    },
    _add_kanban_dropdown: function() {
        this.do({
            type: 'kanban_dropdown',
        });
    },
    _add_kanban_priority: function(data) {
        this.do({
            type: 'kanban_priority',
            field: data.field,
        });
    },
    _add_kanban_image: function(data) {
        this.do({
            type: 'kanban_image',
            field: data.field,
        });
    },
    _remove_element: function(type, node, xpath_info) {
        // After the element removal, if the parent doesn't contain any children
        // anymore, the parent node is also deleted (except if the parent is
        // the only remaining node)
        var parent_node = find_parent(this.fields_view.arch, node);
        var is_root = !find_parent(this.fields_view.arch, parent_node);
        if (parent_node.children.length === 1 && !is_root) {
            node = parent_node;
        }

        this.do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.exprAttrs[node.tag]),
                xpath_info: xpath_info,
            },
        });
        this._onUnselectElement();
    },
    _edit_view_attributes: function(type, new_attrs) {
        this.do({
            type: type,
            target: {
                tag: this.viewType === 'list' ? 'tree' : this.viewType,
            },
            position: 'attributes',
            new_attrs: new_attrs,
        });
    },
    _edit_attributes_element: function(type, node, xpath_info, new_attrs) {
        this.do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.exprAttrs[node.tag]),
                xpath_info: xpath_info,
            },
            position: 'attributes',
            node: node,
            new_attrs: new_attrs,
        });
    },
    _add_filter: function(type, node, xpath_info, position, new_attrs) {
        this.do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.exprAttrs[node.tag]),
                xpath_info: xpath_info,
            },
            position: position,
            node: {
                tag: 'filter',
                attrs: new_attrs,
            },
        });
    },
    _add_separator: function (type, node, xpath_info, position) {
        this.do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.exprAttrs[node.tag]),
                xpath_info: xpath_info,
            },
            position: position,
            node: {
                tag: 'separator',
                attrs: {
                    name: 'studio_separator_' + utils.randomString(5),
                },
            },
        });
    },
    _get_fields_not_in_view: function() {
        // Remove fields that are already in the view
        var fields_not_in_view = _.omit(this.fields, Object.keys(this.fieldsView.fields));
        // Convert dict to array
        var list = _.map(fields_not_in_view, function(dict, key) {
            return _.extend({name: key}, dict);
        });
        // Sort by field_description (alphabetically)
        return _.sortBy(list, 'string');
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    _onUnselectElement: function () {
        this.editor.selected_node_id = false;
        this.editor.unselectedElements();
    },

    toggle_editor_sidebar: function (event) {
        var node = event.data.node;
        var mode = node.tag;

        var def;
        var params = {node: node};
        if (mode === 'field') {
            var field = this.fieldsView.fields[node.attrs.name];
            params.field = field;
            def = customize.get_default_value(this.modelName, node.attrs.name);
        }
        if (mode === 'div' && node.attrs.class === 'oe_chatter') {
            def = customize.get_email_alias(this.modelName);
        }
        var self = this;
        $.when(def).then(function(result) {
            _.extend(params, result);
            self.sidebar.toggle_mode('properties', params);
        });
    },
    toggle_form_invisible: function (event) {
        this.updateEditor(true, {show_invisible: event.data.show_invisible});
    },
    open_xml_editor: function () {
        var self = this;

        this.XMLEditor = new XMLEditor(this, this.view_id, {
            position: 'left',
            doNotLoadLess: true,

        });
        this.mode = 'rendering';

        $.when(this.updateEditor(), this.XMLEditor.prependTo(this.$el)).then(function() {
            self.sidebar.$el.detach();
            $('body').addClass('o_in_studio_xml_editor');
        });
    },
    close_xml_editor: function () {
        this.mode = 'edition';
        this.updateEditor(true);
        this.XMLEditor.destroy();
        this.sidebar.prependTo(this.$el);
        $('body').removeClass('o_in_studio_xml_editor');
    },
    save_xml_editor: function (event) {
        this.do({
            type: 'replace_arch',
            view_id: event.data.view_id,
            old_arch: event.data.old_arch,
            new_arch: event.data.new_arch,
        }).then(function() {
            if (event.data.on_success) {
                event.data.on_success();
            }
        });
    },
    open_defaults: function() {
        var options = {
            keep_state: true,
        };
        this.do_action({
            name: _t('Default Values'),
            type: 'ir.actions.act_window',
            res_model: 'ir.values',
            target: 'current',
            views: [[false, 'list'], [false, 'form']],
            domain: [['model', '=', this.modelName], ['key', '=', 'default']],
        }, options);
    },
    open_view_form: function() {
        var options = {
            keep_state: true,
        };
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'ir.ui.view',
            res_id: this.view_id,
            views: [[false, 'form']],
            target: 'current',
        }, options);
    },
    open_field_form: function(event) {
        var self = this;
        var field_name = event.data.field_name;
        var Fields = new BasicModel('ir.model.fields');
        Fields.query(['id'])
              .filter([['model', '=', this.modelName], ['name', '=', field_name]])
              .all().then(function(result) {
                var res_id = result && result[0].id;
                if (res_id) {
                    var options = {
                        keep_state: true,
                    };
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'ir.model.fields',
                        res_id: res_id,
                        views: [[false, 'form']],
                        target: 'current',
                    }, options);
                }
        });
    },
    show_nearest_hook: function (event) {
        var is_nearest_hook = this.editor.highlightNearestHook(event.data.$helper, event.data.position);
        event.data.$helper.toggleClass('ui-draggable-helper-ready', is_nearest_hook);
    },
    update_view: function(event) {
        var structure = event.data.structure;
        var type = event.data.type;
        var node = event.data.node;
        var new_attrs = event.data.new_attrs || {};
        var position = event.data.position || 'after';
        var xpath_info;
        if (node && !_.pick(node.attrs, this.exprAttrs[node.tag]).length) {
            xpath_info = find_parents_positions(this.fieldsView.arch, node);
        }

        switch (structure) {
            case 'text':
                break;
            case 'picture':
                break;
            case 'group':
                this._add_element(type, node, xpath_info, position, 'group');
                break;
            case 'buttonbox':
                this._add_buttonbox();
                break;
            case 'button':
                this._add_button(type);
                break;
            case 'notebook':
                this._add_element(type, node, xpath_info, position, 'notebook');
                break;
            case 'page':
                this._add_page(type, node, xpath_info, position);
                break;
            case 'field':
                var field_description = event.data.field_description;
                this._add_field(type, field_description, node, xpath_info, position, new_attrs);
                break;
            case 'chatter':
                this._add_chatter(event.data);
                break;
            case 'kanban_dropdown':
                this._add_kanban_dropdown();
                break;
            case 'kanban_priority':
                this._add_kanban_priority(event.data);
                break;
            case 'kanban_image':
                this._add_kanban_image(event.data);
                break;
            case 'remove':
                this._remove_element(type, node, xpath_info);
                break;
            case 'view_attribute':
                this._edit_view_attributes(type, new_attrs);
                break;
            case 'edit_attributes':
                this._edit_attributes_element(type, node, xpath_info, new_attrs);
                break;
            case 'filter':
                this._add_filter(type, node, xpath_info, position, new_attrs);
                break;
            case 'separator':
                this._add_separator(type, node, xpath_info, position);
                break;
        }
    },
    set_email_alias: function(event) {
        var value = event.data.value;
        customize.set_email_alias(this.modelName, value);
    },
    set_default_value: function(event) {
        var data = event.data;
        return customize
            .set_default_value(this.model, data.field_name, data.value)
            .fail(function() {
                if (data.on_fail) {
                    data.on_fail();
                }
            });
    },
});

});
