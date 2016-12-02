odoo.define('web_studio.ViewEditorManager', function (require) {
"use strict";

var core = require('web.core');
var data_manager = require('web.data_manager');
var field_registry = require('web.field_registry');
var form_common = require('web.form_common');
var Model = require('web.Model');
var web_utils = require("web.utils");
var ViewModel = require('web.ViewModel');
var Widget = require('web.Widget');

var bus = require('web_studio.bus');
var customize = require('web_studio.customize');

var FormRenderer = require('web.FormRenderer');
var KanbanRenderer = require('web.KanbanRenderer');
var ListRenderer = require('web.BasicListRenderer');

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

var Renderers = {
    form: FormRenderer,
    kanban: KanbanRenderer,
    list: ListRenderer,
    grid: GridEditor,
    pivot: PivotEditor,
    graph: GraphEditor,
    calendar: CalendarEditor,
    gantt: GanttEditor,
    search: SearchEditor,
};

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
        'unselect_element': 'unselect_element',
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
    },

    init: function (parent, model, fields_view, view_type, dataset, options) {
        var self = this;
        this._super.apply(this, arguments);
        this.model = model;
        this.fields_view = fields_view;
        this.view_type = view_type;
        this.dataset = dataset;
        this.view_id = this.fields_view.view_id;
        this.view_attrs = this.fields_view.arch.attrs;
        this.mode = 'edition';  // the other mode is 'rendering' when using the XML editor
        this.editor = undefined;
        this.sidebar = undefined;
        this.operations = [];
        this.operations_undone = [];
        this.expr_attrs = {
            'field': ['name'],
            'label': ['for'],
            'page': ['name'],
            'group': ['name'],
            'div': ['class'],
            'button': ['name'],
        };
        this.ids = options.ids || [];
        this.res_id = options.res_id;
        this.chatter_allowed = options.chatter_allowed;
        this.studio_view_id = options.studio_view_id;
        this.studio_view_arch = options.studio_view_arch;

        this._apply_changes_mutex = new web_utils.Mutex();

        bus.on('undo_clicked', this, this.undo);
        bus.on('redo_clicked', this, this.redo);
    },
    willStart: function() {
        var self = this;
        return $.when(
            this.load_demo_data(),
            this.get_fields(),
            this._super.apply(this, arguments)
        ).then(function (demo_data, fields) {
            self.demo_data = demo_data;
            self.fields = fields;
            // Fields not already in view
            var fields_not_in_view = _.omit(self.fields, Object.keys(self.fields_view.fields));
            self.sidebar = new ViewEditorSidebar(self, self.view_type, self.view_attrs, self.model, fields_not_in_view);
        });
    },
    start: function () {
        var self = this;
        this.$renderer_container = $('<div>').addClass('o_web_studio_view_renderer');
        this.$el.append(this.$renderer_container);
        return $.when(this._super(), this.render_content()).then(function () {
            return self.sidebar.prependTo(self.$el);
        });
    },
    get_fields: function() {
        return data_manager.load_fields(this.dataset);
    },
    load_demo_data: function() {
        var self = this;
        var def;
        var datamodel = new ViewModel();
        var fields = this.fields_view.fields;

        if (this.view_type === 'form') {
            var domain = this.res_id ? [['id', '=', this.res_id]] : [];
            // FIXME: this is an hack to load an existing record
            def = datamodel.load(this.model, {domain: domain, limit: 1, fields: {id: {}}}).then(function (result) {
                var data = datamodel.get(result);
                var res_id = data.data[0] && data.data[0].res_id || false;
                return datamodel.load(self.model, {id: res_id, fields: fields});
            });
        } else if (this.view_type === 'search') {
            return;
        } else {
            def = datamodel.load(this.model, {
                fields: fields,
                domain: [['id', 'in', this.ids]],
                grouped_by: [],
                limit: 20,
                many2manys: [], // fixme: find many2manys
                m2m_context: [], // fixme: find m2m context
            });
        }
        return def.then(function (db_id) {
            return datamodel.get(db_id);
        });
    },
    render_content: function (replace, options) {
        var self = this;
        var editor;
        var def;
        var renderer_scrolltop = this.$renderer_container.scrollTop();
        var local_state = this.editor ? this.editor.get_local_state() : false;

        options = _.extend({}, options, {chatter_allowed: this.chatter_allowed});
        if (this.mode === 'edition') {
            if (replace || !this.editor) {
                var Editor = Editors[this.view_type];
                editor = new Editor(this, this.fields_view.arch, this.fields_view.fields, this.demo_data, field_registry, options);
                // Update fields and render the sidebar
                var fields_not_in_view = _.omit(this.fields, Object.keys(this.fields_view.fields));
                this.sidebar.update_fields(fields_not_in_view);
            }
        } else {
            var Renderer = Renderers[this.view_type];
            editor = new Renderer(this, this.fields_view.arch, this.fields_view.fields, this.demo_data, field_registry, options);
        }

        if (this.editor) {
            this.editor.destroy();
        }
        if (editor) {
            this.editor = editor;
            try {
                // Starting renderers is synchronous, but it's not the case for old views
                def = this.editor.appendTo(this.$renderer_container).then(function() {
                    self.$renderer_container.scrollTop(renderer_scrolltop); // restore scroll position
                });
            } catch(e) {
                this.do_warn(_t("Error"), _t("The requested change caused an error in the view.  It could be because a field was deleted, but still used somewhere else."));
                this.undo(true);
            }
        }

        return $.when(def).then(function() {
            if (local_state) {
                self.editor.set_local_state(local_state);
            }
        });
    },
    toggle_editor_sidebar: function (event) {
        var node = event.data.node;
        var mode = node.tag;

        var def;
        var params = {node: node};
        if (mode === 'field') {
            var field = this.fields_view.fields[node.attrs.name];
            params.field = field;
            def = customize.get_default_value(this.model, node.attrs.name);
        }
        if (mode === 'div' && node.attrs.class === 'oe_chatter') {
            def = customize.get_email_alias(this.model);
        }
        var self = this;
        $.when(def).then(function(result) {
            _.extend(params, result);
            self.sidebar.toggle_mode('properties', params);
        });
    },
    toggle_form_invisible: function (event) {
        this.render_content(true, {show_invisible: event.data.show_invisible});
    },
    open_xml_editor: function () {
        var self = this;

        this.XMLEditor = new XMLEditor(this, this.view_id, {'position': 'left'});
        this.mode = 'rendering';

        $.when(this.render_content(), this.XMLEditor.prependTo(this.$el)).then(function() {
            self.sidebar.$el.detach();
        });
    },
    close_xml_editor: function () {
        this.mode = 'edition';
        this.render_content(true);
        this.XMLEditor.destroy();
        this.sidebar.prependTo(this.$el);
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
        this.do_action({
            name: _t('Default Values'),
            type: 'ir.actions.act_window',
            res_model: 'ir.values',
            target: 'current',
            views: [[false, 'list'], [false, 'form']],
            domain: [['model', '=', this.model], ['key', '=', 'default']],
        });
    },
    open_view_form: function() {
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'ir.ui.view',
            res_id: this.view_id,
            views: [[false, 'form']],
            target: 'current',
        });
    },
    open_field_form: function(event) {
        var self = this;
        var field_name = event.data.field_name;
        var Fields = new Model('ir.model.fields');
        Fields.query(['id'])
              .filter([['model', '=', this.model], ['name', '=', field_name]])
              .all().then(function(result) {
                var res_id = result && result[0].id;
                if (res_id) {
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'ir.model.fields',
                        res_id: res_id,
                        views: [[false, 'form']],
                        target: 'current',
                    });
                }
        });
    },
    update_view: function(event) {
        var structure = event.data.structure;
        var type = event.data.type;
        var node = event.data.node;
        var new_attrs = event.data.new_attrs || {};
        var position = event.data.position || 'after';
        var xpath_info;
        if (node && !_.pick(node.attrs, this.expr_attrs[node.tag]).length) {
            xpath_info = find_parents_positions(this.fields_view.arch, node);
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
                this._add_buttonbox(type);
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
            case 'remove':
                this._remove_element(type, node, xpath_info);
                break;
            case 'view_attribute':
                this._edit_view_attributes(type, new_attrs);
                break;
            case 'edit_attributes':
                this._edit_attributes_element(type, node, xpath_info, new_attrs);
                break;
        }
    },
    set_email_alias: function(event) {
        var value = event.data.value;
        customize.set_email_alias(this.model, value);
    },
    set_default_value: function(event) {
        var value = event.data.value;
        var field_name = event.data.field_name;
        customize.set_default_value(this.model, field_name, value);
    },
    do: function(op) {
        this.operations.push(op);
        this.operations_undone = [];

        return this.apply_changes(false, op.type === 'replace_arch');
    },
    undo: function(forget) {
        if (!this.operations.length) {
            return;
        }
        var op = this.operations.pop();
        if (!forget) {
            this.operations_undone.push(op);
        }

        if (op.type === 'replace_arch') {
            // as the whole arch has been replace (A -> B),
            // when undoing it, the operation (B -> A) is added and
            // removed just after.
            var undo_op = jQuery.extend(true, {}, op);
            undo_op.old_arch = op.new_arch;
            undo_op.new_arch = op.old_arch;
            this.operations.push(undo_op);
            return this.apply_changes(true, true);
        } else {
            return this.apply_changes(false, false);
        }
    },
    redo: function() {
        if (!this.operations_undone.length) {
            return;
        }
        var op = this.operations_undone.pop();
        this.operations.push(op);

        return this.apply_changes(false, op.type === 'replace_arch');
    },
    update_buttons: function() {
        // Undo button
        if (this.operations.length) {
            bus.trigger('undo_available');
        } else {
            bus.trigger('undo_not_available');
        }

        // Redo button
        if (this.operations_undone.length) {
            bus.trigger('redo_available');
        } else {
            bus.trigger('redo_not_available');
        }
    },
    apply_changes: function(remove_last_op, from_xml) {
        var self = this;

        var last_op = this.operations.slice(-1)[0];

        var def;
        if (from_xml) {
            def = this._apply_changes_mutex.exec(customize.edit_view_arch.bind(
                customize,
                last_op.view_id,
                last_op.new_arch
            ));
        } else {
            def = this._apply_changes_mutex.exec(customize.edit_view.bind(
                customize,
                this.view_id,
                this.studio_view_arch,
                _.filter(this.operations, function(el) {return el.type !== 'replace_arch'; })
            ));
        }

        return def.then(function (result) {
            if (!result.fields_view) {
                self.do_warn(_t("Error"), _t("This operation caused an error, probably because a xpath was broken"));
                return self.undo(true).then(function () {
                    return $.Deferred().reject(); // indicate that the operation can't be applied
                });
            }
            // "/web_studio/edit_view" returns "fields" only when we created a new field.
            if (result.fields) {
                self.fields = result.fields;
            }
            self.fields_view = data_manager._postprocess_fvg(result.fields_view);

            // As the studio view arch is stored in this widget, if this view
            // is updated directly with the XML editor, the arch should be updated.
            // The operations may not have any sense anymore so they are dropped.
            if (from_xml && last_op.view_id === self.studio_view_id) {
                self.studio_view_arch = last_op.new_arch;
                self.operations = [];
                self.operations_undone = [];
            }
            if (remove_last_op) { self.operations.pop(); }
            self.update_buttons();

            return self.load_demo_data().then(function(demo_data) {
                self.demo_data = demo_data;
                self.render_content(true);
            });
        });
    },
    unselect_element: function() {
        if (this.editor && this.editor._reset_clicked_style) {
            this.editor.selected_node_id = false;
            this.editor._reset_clicked_style(); // FIXME: this function should be written in an AbstractEditor
        }
    },
    _add_element: function(type, node, xpath_info, position, tag) {
        this.do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.expr_attrs[node.tag]),
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
    _add_buttonbox: function(type) {
        this.do({
            type: 'buttonbox',
        });
    },
    _add_button: function(type) {
        var dialog = new NewButtonBoxDialog(this, this.model).open();
        dialog.on('saved', this, function(result) {
            this.do({
                type: type,
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
    },
    _add_page: function(type, node, xpath_info, position) {
        this.do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.expr_attrs[node.tag]),
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
            field_description.name = 'x_studio_field_' + utils.randomString(5);
            field_description.model_name = this.model;
            // Fields with requirements
            // Open Dialog to precise the required fields for this field.
            if (_.contains(['selection', 'one2many', 'many2one', 'many2many'], field_description.ttype)) {
                def_field_values = $.Deferred();
                var dialog = new NewFieldDialog(this, this.model, field_description.ttype).open();
                dialog.on('field_default_values_saved', this, function(values) {
                    def_field_values.resolve(values);
                    dialog.close();
                });
            }
        }
        // When the field is created, close the dialog and update the view
        $.when(def_field_values).then(function(values) {
            self.do({
                type: type,
                target: {
                    tag: node.tag,
                    attrs: _.pick(node.attrs, self.expr_attrs[node.tag]),
                    xpath_info: xpath_info,
                },
                position: position,
                node: {
                    tag: 'field',
                    attrs: new_attrs,
                    field_description: _.extend(field_description, values),
                },
            });
        });
    },
    _add_chatter: function(data) {
        this.do({
            type: 'chatter',
            model: this.model,
            remove_message_ids: data.remove_message_ids,
            remove_follower_ids: data.remove_follower_ids,
        });
    },
    _remove_element: function(type, node, xpath_info) {
        // We want to check if the parent of the node if not empty
        // If the parent contains only the node we want to delete
        // We will delete the parent instead of the node
        var parent_node = find_parent(this.fields_view.arch, node);
        if (parent_node.children.length === 1) {
            node = parent_node;
        }

        this.do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.expr_attrs[node.tag]),
                xpath_info: xpath_info,
            },
        });
    },
    _edit_view_attributes: function(type, new_attrs) {
        this.do({
            type: type,
            target: {
                tag: this.view_type === 'list' ? 'tree' : this.view_type,
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
                attrs: _.pick(node.attrs, this.expr_attrs[node.tag]),
                xpath_info: xpath_info,
            },
            position: 'attributes',
            node: node,
            new_attrs: new_attrs,
        });
    },
    destroy: function() {
        bus.trigger('undo_not_available');
        bus.trigger('redo_not_available');

        this._super.apply(this, arguments);
    }
});

});
