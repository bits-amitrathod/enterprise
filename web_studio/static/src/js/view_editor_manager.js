odoo.define('web_studio.ViewEditorManager', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var concurrency = require('web.concurrency');
var core = require('web.core');
var data_manager = require('web.data_manager');
var Dialog = require('web.Dialog');
var session = require('web.session');
var view_registry = require('web.view_registry');
var Widget = require('web.Widget');

var bus = require('web_studio.bus');

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

var ViewEditorManager = Widget.extend({
    className: 'o_web_studio_view_editor',
    custom_events: {
        'sidebar_tab_changed': '_onSidebarTabChanged',
        'node_clicked': '_onNodeClicked',
        'unselect_element': '_onUnselectElement',
        'view_change': '_onViewChange',
        'email_alias_change': '_onEmailAliasChange',
        'default_value_change': '_onDefaultValueChange',
        'toggle_form_invisible': '_onShowInvisibleToggled',
        'open_xml_editor': '_onOpenXMLEditor',
        'close_xml_editor': '_onCloseXMLEditor',
        'save_xml_editor': '_onSaveXMLEditor',
        'open_view_form': '_onOpenViewForm',
        'open_defaults': '_onOpenDefaults',
        'open_field_form': '_onOpenFieldForm',
        'drag_component' : '_onComponentDragged',
    },
    /**
     * @override
     * @param {Widget} parent
     * @param {Object} params
     * @param {Object} params.fields_view
     * @param {Object} params.view_env - view manager environment (id, context, etc.)
     * @param {Object} [params.chatter_allowed]
     * @param {Object} [params.studio_view_id]
     * @param {Object} [params.studio_view_arch]
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);

        this.fields_view = params.fields_view;
        this.model_name = this.fields_view.model;
        this.fields = this.fields_view.fields;
        this.view_type = this.fields_view.type;
        this.view_id = this.fields_view.view_id;
        this.mode = 'edition';  // the other mode is 'rendering' in XML editor
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
            'filter': ['name'],
        };
        this.view_env = params.view_env;
        this.chatter_allowed = params.chatter_allowed;
        this.studio_view_id = params.studio_view_id;
        this.studio_view_arch = params.studio_view_arch;

        this._apply_changes_mutex = new concurrency.Mutex();

        bus.on('undo_clicked', this, this.undo);
        bus.on('redo_clicked', this, this.redo);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            return self.instantiateEditor().then(function (editor) {
                var $editorFragment = $('<div>', {
                    class: 'o_web_studio_view_renderer',
                });
                self.editor = editor;
                self.editor.appendTo($editorFragment);
                $editorFragment.appendTo(self.$el);

                self.sidebar = self.instantiateSidebar();
                return self.sidebar.prependTo(self.$el);
            });
        });
    },
    /**
     * @override
     */
    destroy: function () {
        bus.trigger('undo_not_available');
        bus.trigger('redo_not_available');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Apply the changes, i.e. the stack of operations on the Studio view.
     *
     * @param {Boolean} remove_last_op
     * @param {Boolean} from_xml
     * @returns {Deferred}
     */
    applyChanges: function (remove_last_op, from_xml) {
        var self = this;

        var last_op = this.operations.slice(-1)[0];

        var def;
        if (from_xml) {
            def = this._apply_changes_mutex.exec(this._editViewArch.bind(
                this,
                last_op.view_id,
                last_op.new_arch
            )).fail(function () {
                self.trigger_up('studio_error', {error: 'view_rendering'});
            });
        } else {
            def = this._apply_changes_mutex.exec(this._editView.bind(
                this,
                this.view_id,
                this.studio_view_arch,
                _.filter(this.operations, function (el) {return el.type !== 'replace_arch'; })
            ));
        }

        return def.then(function (result) {
            if (!result.fields_views) {
                // the operation can't be applied
                self.trigger_up('studio_error', {error: 'wrong_xpath'});
                return self.undo(true).then(function () {
                    return $.Deferred().reject();
                });
            }
            // transform arch from string to object
            result.fields_views = _.mapObject(result.fields_views, data_manager._postprocess_fvg.bind(data_manager));

            // "/web_studio/edit_view" returns "fields" only when we created a
            // new field ; otherwise, use the same ones that shouldn't have changed.
            var fields = $.extend(true, {}, result.fields || self.fields);

            // add necessary keys on fields_views
            data_manager.processViews(result.fields_views, fields);

            self.fields_view = result.fields_views[self.view_type];
            self.fields = self.fields_view.fields;

            // As the studio view arch is stored in this widget, if this view
            // is updated directly with the XML editor, the arch should be updated.
            // The operations may not have any sense anymore so they are dropped.
            if (from_xml && last_op.view_id === self.studio_view_id) {
                self.studio_view_arch = last_op.new_arch;
                self.operations = [];
                self.operations_undone = [];
            }
            if (remove_last_op) { self.operations.pop(); }

            // fields and fields_view has been updated so let's update everything
            // (i.e. the sidebar which displays the 'Existing Fields', etc.)
            return self.updateEditor().then(function () {
                self.updateButtons();
                if (self.sidebar.state.mode !== 'properties') {
                    // TODO: the sidebar will be updated by clicking on the node
                    self.updateSidebar(self.sidebar.state.mode);
                }
            });
        });
    },
    /**
     * @param {Object} op
     * @returns {Deferred}
     */
    do: function (op) {
        this.operations.push(op);
        this.operations_undone = [];

        return this.applyChanges(false, op.type === 'replace_arch');
    },
    /**
     * @returns {Deferred}
     */
    instantiateEditor: function (params) {
        params = params || {};
        var editor_params = _.defaults(params, {
            mode: 'readonly',
            chatter_allowed: this.chatter_allowed,
            show_invisible: this.sidebar && this.sidebar.state.show_invisible,
            arch: this.fields_view.arch,
        });

        if (this.view_type === 'list') {
            editor_params.hasSelectors = false;
        }

        var View = view_registry.get(this.view_type);
        this.view = new View(this.fields_view, this.view_env);
        var def;
        if (this.mode === 'edition') {
            var Editor = Editors[this.view_type];
            def = this.view.createStudioEditor(this, Editor, editor_params);
        } else {
            def = this.view.createStudioRenderer(this);
        }
        return def;
    },
    /**
     * @private
     * @returns {Widget} A ViewEditorSidebar
     */
    instantiateSidebar: function (state) {

        var defaultMode = _.contains(['form', 'list', 'search'], this.view_type) ? 'new' : 'view';

        state = _.defaults(state || {}, {
            mode: defaultMode,
            attrs: defaultMode === 'view' ? this.fields_view.arch.attrs : {},
        });
        var params = {
            view_type: this.view_type,
            model_name: this.model_name,
            fields: this.fields,
            state: state,
        };

        if (_.contains(['list', 'form', 'kanban'], this.view_type)) {
            var fields_in_view = _.pick(this.fields, this.editor.state.getFieldNames());
            var fields_not_in_view = _.omit(this.fields, this.editor.state.getFieldNames());
            params.fields_not_in_view = fields_not_in_view;
            params.fields_in_view = fields_in_view;
        }

        return new ViewEditorSidebar(this, params);
    },
    /**
     * Redo the last operation.
     *
     * @returns {Deferred}
     */
    redo: function () {
        if (!this.operations_undone.length) {
            return;
        }
        var op = this.operations_undone.pop();
        this.operations.push(op);

        return this.applyChanges(false, op.type === 'replace_arch');
    },
    /**
     * Update the undo/redo button according to the operation stack.
     */
    updateButtons: function () {
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
    /**
     * @param {Object} options
     * @returns {Deferred}
     */
    updateEditor: function (options) {
        var self = this;
        var oldEditor;
        var renderer_scrolltop = this.$el.scrollTop();
        var local_state = this.editor ? this.editor.getLocalState() : false;

        oldEditor = this.editor;
        return this.instantiateEditor(options).then(function (editor) {
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
                self.trigger_up('studio_error', {error: 'view_rendering'});
                self.undo(true);
            }
        });
    },
    /**
     * Re-render the sidebar and destroy the old while keeping the scroll
     * position.
     * If mode is not specified, the sidebar will be renderered with the same
     * state.
     *
     * @param {String} [mode]
     * @returns {Deferred}
     */
    updateSidebar: function (mode, node) {
        var self = this;

        // TODO: scroll top is calculated to 'o_web_studio_sidebar_content'
        var scrolltop = this.sidebar.$el.scrollTop();
        var oldSidebar = this.sidebar;

        var def = [];

        var newState;
        if (mode) {
            newState = {
                mode: mode,
                show_invisible: oldSidebar.state.show_invisible,
            };
        } else {
            newState = oldSidebar.state;
        }

        switch (mode) {
            case 'view':
                newState = _.extend(newState, {
                    attrs: this.fields_view.arch.attrs,
                });
                break;
            case 'new':
                break;
            case 'properties':
                var attrs;
                if (node.tag === 'field') {
                    var viewType = this.editor.state.viewType;
                    attrs = this.editor.state.fieldsInfo[viewType][node.attrs.name];
                } else {
                    attrs = node.attrs;
                }
                newState = _.extend(newState, {
                    node: node,
                    attrs: attrs,
                });

                if (node.tag === 'field') {
                    def = this._getDefaultValue(this.model_name, node.attrs.name);
                }
                if (node.tag === 'div' && node.attrs.class === 'oe_chatter') {
                    def = this._getEmailAlias(this.model_name);
                }
                break;
        }

        return $.when(def).then(function (result) {
            _.extend(newState, result);
            var newSidebar = self.instantiateSidebar(newState);
            self.sidebar = newSidebar;

            return newSidebar.prependTo(self.$el).then(function () {
                oldSidebar.destroy();

                // restore previous state
                newSidebar.$el.scrollTop(scrolltop);

                if (self.mode === 'rendering') {
                    newSidebar.$el.detach();
                }
            });
        });
    },
    /**
     * Undo the last operation.
     *
     * @param {Boolean} forget
     * @returns {Deferred}
     */
    undo: function (forget) {
        if (!this.operations.length) {
            return $.Deferred().resolve();
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
            return this.applyChanges(true, true);
        } else {
            return this.applyChanges(false, false);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {String} type
     */
    _addButton: function (data) {
        var dialog = new NewButtonBoxDialog(this, this.model_name).open();
        dialog.on('saved', this, function (result) {
            if (data.add_buttonbox) {
                this.operations.push({type: 'buttonbox'});
            }
            this.do({
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
    },
    /**
     * @private
     * @param {Object} data
     */
    _addChatter: function (data) {
        this.do({
            type: 'chatter',
            model: this.model_name,
            remove_message_ids: data.remove_message_ids,
            remove_follower_ids: data.remove_follower_ids,
        });
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} node
     * @param {Object} xpath_info
     * @param {String} position
     * @param {String} tag
     */
    _addElement: function (type, node, xpath_info, position, tag) {
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
    /**
     * @private
     * @param {String} type
     * @param {Object} field_description
     * @param {Object} node
     * @param {Object} xpath_info
     * @param {String} position
     * @param {Object} new_attrs
     */
    _addField: function (type, field_description, node, xpath_info, position, new_attrs) {
        var self = this;
        var def_field_values;

        // The field doesn't exist: field_description is the definition of the new field.
        // No need to have field_description of an existing field
        if (field_description) {
            // "extend" avoids having the same reference in "this.operations"
            // We can thus modify it without editing previous existing operations
            field_description = _.extend({}, field_description, {
                name: 'x_studio_field_' + utils.randomString(5),
                model_name: this.model_name,
            });
            // Fields with requirements
            // Open Dialog to precise the required fields for this field.
            if (_.contains(['selection', 'one2many', 'many2one', 'many2many', 'related'], field_description.ttype)) {
                def_field_values = $.Deferred();
                var dialog = new NewFieldDialog(this, this.model_name, field_description.ttype, this.fields).open();
                dialog.on('field_default_values_saved', this, function (values) {
                    def_field_values.resolve(values);
                    dialog.close();
                });
                dialog.on('closed', this, function () {
                    def_field_values.reject();
                });
            }
            if (field_description.ttype === 'monetary') {
                def_field_values = $.Deferred();
                // Detect currency_id on the current model
                new BasicModel("ir.model.fields").call("search", [[
                    ['name', '=', 'currency_id'],
                    ['model', '=', this.model_name],
                    ['relation', '=', 'res.currency'],
                ]]).then(function (data) {
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
        $.when(def_field_values).then(function (values) {
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
        }).fail(function () {
            self.updateEditor();
        });
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} node
     * @param {Object} xpath_info
     * @param {String} position
     * @param {Object} new_attrs
     */
    _addFilter: function (type, node, xpath_info, position, new_attrs) {
        this.do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.expr_attrs[node.tag]),
                xpath_info: xpath_info,
            },
            position: position,
            node: {
                tag: 'filter',
                attrs: new_attrs,
            },
        });
    },
    /**
     * @private
     */
    _addKanbanDropdown: function () {
        this.do({
            type: 'kanban_dropdown',
        });
    },
    /**
     * @private
     * @param {Object} data
     */
    _addKanbanPriority: function (data) {
        this.do({
            type: 'kanban_priority',
            field: data.field,
        });
    },
    /**
     * @private
     * @param {Object} data
     */
    _addKanbanImage: function (data) {
        this.do({
            type: 'kanban_image',
            field: data.field,
        });
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} node
     * @param {Object} xpath_info
     * @param {String} position
     */
    _addPage: function (type, node, xpath_info, position) {
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
    /**
     * @private
     * @param {String} type
     * @param {Object} node
     * @param {Object} xpath_info
     * @param {String} position
     */
    _addSeparator: function (type, node, xpath_info, position) {
        this.do({
            type: type,
            target: {
                tag: node.tag,
                attrs: _.pick(node.attrs, this.expr_attrs[node.tag]),
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
    /**
     * @private
     * @param {String} type
     * @param {Object} node
     * @param {Object} xpath_info
     * @param {Object} new_attrs
     */
    _editElementAttributes: function (type, node, xpath_info, new_attrs) {
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
    /**
     * The point of this function is to receive a list of customize operations
     * to do.
     *
     * @private
     * @param {Integer} view_id
     * @param {String} studio_view_arch
     * @param {Array} operations
     * @returns {Deferred}
     */
    _editView: function (view_id, studio_view_arch, operations) {
        data_manager.invalidate();
        return this._rpc({
            route: '/web_studio/edit_view',
            params: {
                view_id: view_id,
                studio_view_arch: studio_view_arch,
                operations: operations,
                context: session.user_context,
            },
        });
    },
    /**
     * This is used when the view is edited with the XML editor: the whole arch
     * is replaced by a new one.
     *
     * @private
     * @param {Integer} view_id
     * @param {String} view_arch
     * @returns {Deferred}
     */
    _editViewArch: function (view_id, view_arch) {
        data_manager.invalidate();
        return this._rpc({
            route: '/web_studio/edit_view_arch',
            params: {
                view_id: view_id,
                view_arch: view_arch,
                context: session.user_context,
            },
        });
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} new_attrs
     */
    _editViewAttributes: function (type, new_attrs) {
        this.do({
            type: type,
            target: {
                tag: this.view_type === 'list' ? 'tree' : this.view_type,
            },
            position: 'attributes',
            new_attrs: new_attrs,
        });
    },
    /**
     * @private
     * @param {String} model_name
     * @param {String} field_name
     * @returns {Deferred}
     */
    _getDefaultValue: function (model_name, field_name) {
        return this._rpc({
            route: '/web_studio/get_default_value',
            params: {
                model_name: model_name,
                field_name: field_name,
            },
        });
    },
    /**
     * @private
     * @param {String} model_name
     * @returns {Deferred}
     * @returns {Deferred}
     */
    _getEmailAlias: function (model_name) {
        return this._rpc({
            route: '/web_studio/get_email_alias',
            params: {
                model_name: model_name,
            },
        });
    },
    /**
     * @private
     * @param {String} type
     * @param {Object} node
     * @param {Object} xpath_info
     */
    _removeElement: function (type, node, xpath_info) {
        // After the element removal, if the parent doesn't contain any children
        // anymore, the parent node is also deleted (except if the parent is
        // the only remaining node)
        var parent_node = findParent(this.fields_view.arch, node);
        var is_root = !findParent(this.fields_view.arch, parent_node);
        if (parent_node.children.length === 1 && !is_root) {
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
        this._onUnselectElement();
    },
    /**
     * @private
     * @param {String} model_name
     * @param {String} field_name
     * @param {*} value
     * @returns {Deferred}
     */
    _setDefaultValue: function (model_name, field_name, value) {
        var self = this;
        var def = $.Deferred();
        var params = {
            model_name: model_name,
            field_name: field_name,
            value: value,
        };
        this._rpc({route: '/web_studio/set_default_value', params: params})
            .fail(function (result, error) {
                var alert = Dialog.alert(self, error.data.message);
                alert.on('closed', null, def.reject.bind(def));
            });
        return def;
    },
    /**
     * @private
     * @param {String} model_name
     * @param {[type]} value
     * @returns {Deferred}
     */
    _setEmailAlias: function (model_name, value) {
        return this._rpc({
            route: '/web_studio/set_email_alias',
            params: {
                model_name: model_name,
                value: value,
            },
        });
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     */
    _onCloseXMLEditor: function () {
        this.mode = 'edition';
        this.updateEditor();
        this.XMLEditor.destroy();
        this.sidebar.prependTo(this.$el);
        $('body').removeClass('o_in_studio_xml_editor');
    },
    /**
     * Show nearrest hook.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onComponentDragged: function (event) {
        var is_nearest_hook = this.editor.highlightNearestHook(event.data.$helper, event.data.position);
        event.data.$helper.toggleClass('ui-draggable-helper-ready', is_nearest_hook);
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onDefaultValueChange: function (event) {
        var data = event.data;
        this._setDefaultValue(this.model_name, data.field_name, data.value)
            .fail(function () {
                if (data.on_fail) {
                    data.on_fail();
                }
            });
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onEmailAliasChange: function (event) {
        var value = event.data.value;
        this._setEmailAlias(this.model_name, value);
    },
    /**
     * Toggle editor sidebar.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onNodeClicked: function (event) {
        var node = event.data.node;
        this.updateSidebar('properties', node);
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onOpenDefaults: function () {
        var options = {
            keep_state: true,
            disable_edition: true,
        };
        this.do_action({
            name: _t('Default Values'),
            type: 'ir.actions.act_window',
            res_model: 'ir.values',
            target: 'current',
            views: [[false, 'list'], [false, 'form']],
            domain: [['model', '=', this.model_name], ['key', '=', 'default']],
        }, options);
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onOpenFieldForm: function (event) {
        var self = this;
        var field_name = event.data.field_name;
        this._rpc({
            model: 'ir.model.fields',
            method: 'search_read',
            fields: ['id'],
            domain: [['model', '=', this.model_name], ['name', '=', field_name]],
        }).then(function (result) {
            var res_id = result && result[0].id;
            if (res_id) {
                var options = {
                    keep_state: true,
                    disable_edition: true,
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
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onOpenViewForm: function () {
        var options = {
            keep_state: true,
            disable_edition: true,
        };
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'ir.ui.view',
            res_id: this.view_id,
            views: [[false, 'form']],
            target: 'current',
        }, options);
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onOpenXMLEditor: function () {
        var self = this;

        this.XMLEditor = new XMLEditor(this, this.view_id, {
            position: 'left',
            doNotLoadLess: true,

        });
        this.mode = 'rendering';

        $.when(this.updateEditor(), this.XMLEditor.prependTo(this.$el)).then(function () {
            self.sidebar.$el.detach();
            $('body').addClass('o_in_studio_xml_editor');
        });
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onSaveXMLEditor: function (event) {
        this.do({
            type: 'replace_arch',
            view_id: event.data.view_id,
            old_arch: event.data.old_arch,
            new_arch: event.data.new_arch,
        }).then(function () {
            if (event.data.on_success) {
                event.data.on_success();
            }
        });
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onShowInvisibleToggled: function (event) {
        this.updateEditor({show_invisible: event.data.show_invisible});
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onSidebarTabChanged: function (event) {

        this.updateSidebar(event.data.mode);
        this._onUnselectElement();
    },
    /**
     * @private
     */
    _onUnselectElement: function () {
        this.editor.selected_node_id = false;
        this.editor.unselectedElements();
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onViewChange: function (event) {
        var structure = event.data.structure;
        var type = event.data.type;
        var node = event.data.node;
        var new_attrs = event.data.new_attrs || {};
        var position = event.data.position || 'after';
        var xpath_info;
        if (node && !_.pick(node.attrs, this.expr_attrs[node.tag])) {
            xpath_info = findParentsPositions(this.fields_view.arch, node);
        }

        switch (structure) {
            case 'text':
                break;
            case 'picture':
                break;
            case 'group':
                this._addElement(type, node, xpath_info, position, 'group');
                break;
            case 'button':
                this._addButton(event.data);
                break;
            case 'notebook':
                this._addElement(type, node, xpath_info, position, 'notebook');
                break;
            case 'page':
                this._addPage(type, node, xpath_info, position);
                break;
            case 'field':
                var field_description = event.data.field_description;
                this._addField(type, field_description, node, xpath_info, position, new_attrs);
                break;
            case 'chatter':
                this._addChatter(event.data);
                break;
            case 'kanban_dropdown':
                this._addKanbanDropdown();
                break;
            case 'kanban_priority':
                this._addKanbanPriority(event.data);
                break;
            case 'kanban_image':
                this._addKanbanImage(event.data);
                break;
            case 'remove':
                this._removeElement(type, node, xpath_info);
                break;
            case 'view_attribute':
                this._editViewAttributes(type, new_attrs);
                break;
            case 'edit_attributes':
                this._editElementAttributes(type, node, xpath_info, new_attrs);
                break;
            case 'filter':
                this._addFilter(type, node, xpath_info, position, new_attrs);
                break;
            case 'separator':
                this._addSeparator(type, node, xpath_info, position);
                break;
        }
    },
});

function findParent(arch, node) {
    var parent = arch;
    var result;
    _.each(parent.children, function (child) {
        if (child.attrs && child.attrs.name === node.attrs.name) {
            result = parent;
        } else {
            var res = findParent(child, node);
            if (res) {
                result = res;
            }
        }
    });
    return result;
}

function findParentsPositions(arch, node) {
    return _findParentsPositions(arch, node, [], 1);
}

function _findParentsPositions(parent, node, positions, indice) {
    var result;
    positions.push({
        'tag': parent.tag,
        'indice': indice,
    });
    if (parent === node) {
        return positions;
    } else {
        var current_indices = {};
        _.each(parent.children, function (child) {
            // Save indice of each sibling node
            current_indices[child.tag] = current_indices[child.tag] ? current_indices[child.tag] + 1 : 1;
            var res = _findParentsPositions(child, node, positions, current_indices[child.tag]);
            if (res) {
                result = res;
            } else {
                positions.pop();
            }
        });
    }
    return result;
}

return ViewEditorManager;

});
