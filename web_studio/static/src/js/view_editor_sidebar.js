odoo.define('web_studio.ViewEditorSidebar', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var DomainSelectorDialog = require("web.DomainSelectorDialog");
var domainUtils = require("web.domainUtils");
var field_registry = require('web.field_registry');
var relational_fields = require('web.relational_fields');
var session = require("web.session");
var Widget = require('web.Widget');
var FieldManagerMixin = require('web_studio.FieldManagerMixin');
var view_components = require('web_studio.view_components');

var form_component_widget_registry = view_components.registry;
var _t = core._t;
var Many2ManyTags = relational_fields.FieldMany2ManyTags;

return Widget.extend(FieldManagerMixin, {
    template: 'web_studio.ViewEditorSidebar',
    custom_events: _.extend({}, FieldManagerMixin.custom_events, {
        field_changed: function(event) {
            this.change_field_group(event);
        },
    }),
    events: {
        'click .o_web_studio_new:not(.inactive)': function() {
            this.trigger_up('unselect_element');
            this.toggle_mode('new');
        },
        'click .o_web_studio_view': function() {
            this.trigger_up('unselect_element');
            this.toggle_mode('view');
        },
        'click .o_web_studio_xml_editor': 'on_xml_editor',
        'click .o_display_view .o_web_studio_parameters': 'on_view_parameters',
        'click .o_display_field .o_web_studio_parameters': 'on_field_parameters',
        'click .o_display_view .o_web_studio_defaults': 'on_defaults',
        'change #show_invisible': 'toggle_form_invisible',
        'click .o_web_studio_remove': 'remove_element',
        'change .o_display_view input, .o_display_view select': 'change_view',
        'change .o_display_field input[data-type="attributes"], .o_display_field select': 'change_element',
        'focus .o_display_field input[data-type="attributes"][name="domain"]': 'open_domain_editor',
        'change .o_display_field input[data-type="default_value"]': 'change_default_value',
        'change .o_display_page input': 'change_element',
        'change .o_display_group input': 'change_element',
        'change .o_display_button input': 'change_element',
        'change .o_display_filter input': 'change_element',
        'change .o_display_chatter input[data-type="email_alias"]': 'change_email_alias',
        'click .o_web_studio_attrs': 'edit_attrs_domain',
        'focus .o_display_filter input#domain': 'open_domain_editor',
    },

    init: function (parent, view_type, view_attrs, model, fields, fields_not_in_view, fields_in_view) {
        FieldManagerMixin.init.call(this);
        this._super.apply(this, arguments);
        this.debug = core.debug;
        this.mode = _.contains(['form', 'list', 'search'], view_type) ? 'new' : 'view';
        this.view_type = view_type;
        this.view_attrs = view_attrs || {};
        this.model = model;

        this.fields = fields;
        this.computed_ordered_fields();

        this.fields_not_in_view = fields_not_in_view;
        this.fields_in_view = fields_in_view;
        this.show_invisible = false;

        this.GROUPABLE_TYPES = ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime'];
    },
    renderElement: function() {
        var self = this;
        this._super();

        if (this.mode === 'new') {
            this._append_widgets_components();
            this.$('.o_web_studio_component').on("drag", _.throttle(function(event, ui) {
                self.trigger_up('drag_component', {position: {pageX: event.pageX, pageY: event.pageY}, $helper: ui.helper});
            }, 200));
        } else if (this.mode === 'properties') {
            this._append_widgets_many2many_groups();
        }
    },

    toggle_mode: function(mode, options) {
        this.mode = mode;
        this.node = options && options.node || {};
        this.attrs = this.node.attrs;

        if (options && options.node) {
            this.element = options.node.tag || 'div';
        }

        if (options && options.field) {
            // deep copy of field because the object is modified
            // in this widget and this shouldn't impact it
            var field = jQuery.extend(true, {}, options.field);

            // field_registry contains all widgets
            // We want to filter these widgets based on field types
            this.field_widgets = _.chain(field_registry.map)
                .pairs()
                .filter(function(arr) {
                    return _.contains(arr[1].prototype.supported_field_types, field.type) && !arr[0].includes('.');
                })
                .map(function(array) {
                    return array[0];
                })
                .sortBy()
                .value();

            this.default_value = options.default_value;
            this.attrs = field.__attrs;
            this.element = 'field';
            this.field_parameters = field;
            this.modifiers = JSON.parse(field.__attrs.modifiers);
            this.compute_field_attrs();

            // get infos from the widget:
            // - widget name (to display in the sidebar)
            // - the possibilty to set a placeholder for this widget
            // For example: it's not possible to set it on a boolean field.
            var Widget;
            if (this.attrs.widget) {
                this.widget_name = this.attrs.widget;
                Widget = field_registry.get_any(
                    [this.view_type + '.' + this.widget_name, this.widget_name]
                );
            }
            if (!Widget && (this.view_type === 'form' || this.view_type === 'list')) {
                this.widget_name = field.type;
                Widget = field_registry.get_any(
                    [this.view_type + '.' + this.widget_name, this.widget_name]
                );
            }
            this.has_placeholder = Widget && Widget.prototype.has_placeholder || false;
        } else if (options && options.node.attrs.class === 'oe_chatter') {
            this.element = 'chatter';
            this.email_alias = options.email_alias;
            this.alias_domain = options.alias_domain;
        }
        this.render();
    },
    render: function () {
        var scrollTop = this.$el.scrollTop();
        this.renderElement();
        this.$el.scrollTop(scrollTop);
    },
    update: function (fields, fields_not_in_view, fields_in_view, view_attrs) {
        this.fields = fields;
        this.computed_ordered_fields();
        this.fields_not_in_view = fields_not_in_view;
        this.fields_in_view = fields_in_view;
        this.view_attrs = view_attrs;
        if (this.mode !== 'properties') {
            var scrolltop = this.$('.o_web_studio_sidebar_content').scrollTop();
            this.render();
            this.$('.o_web_studio_sidebar_content').scrollTop(scrolltop);
        }
    },
    computed_ordered_fields: function() {
        // sortBy returns a list so the key (field_name) will be lost but we need it.
        _.each(this.fields, function(element, key) {
            element.key = key;
        });
        this.orderered_fields = _.sortBy(this.fields, 'string');
    },
    compute_field_attrs: function() {
        /* Compute field attributes.
         * These attributes are either taken from modifiers or attrs
         * so attrs store their combinaison.
         */
        this.attrs.invisible = this.modifiers.invisible || this.modifiers.tree_invisible;
        this.attrs.readonly = this.modifiers.readonly;
        this.attrs.string = this.attrs.string || this.field_parameters.string;
        this.attrs.help = this.attrs.help || this.field_parameters.help;
        this.attrs.placeholder = this.attrs.placeholder || this.field_parameters.placeholder;
        this.attrs.required = this.field_parameters.required || this.modifiers.required;
        this.attrs.domain = this.attrs.domain || this.field_parameters.domain;
        this.attrs.context = this.attrs.context || this.field_parameters.context;
        this.attrs.related = this.field_parameters.related ? this.field_parameters.related.join('.'): false;
    },
    _append_widgets_components: function() {
        var self = this;
        var widget_classes;
        var form_widgets;
        var $sidebar_content = this.$('.o_web_studio_sidebar_content');

        // Components
        if (_.contains(['form', 'search'], this.view_type)) {
            widget_classes = form_component_widget_registry.get(this.view_type + '_components');
            form_widgets = widget_classes.map(function(FormComponent) {
                return new FormComponent(self);
            });
            $sidebar_content.append(this._render_widgets_components(form_widgets, 'Components'));
        }
        // New Fields
        if (_.contains(['list', 'form'], this.view_type)) {
            widget_classes = form_component_widget_registry.get('new_field');
            form_widgets = widget_classes.map(function(FormComponent) {
                return new FormComponent(self);
            });
            $sidebar_content.append(this._render_widgets_components(form_widgets, 'New Fields'));
        }

        // Existing Fields
        var FormComponent = form_component_widget_registry.get('existing_field');
        if (this.view_type === 'search') {
            form_widgets = _.map(this.fields, function(field) {
                return new FormComponent(self, field.key, field.string, field.type, field.store);
            });
        } else {
            form_widgets = _.map(this.fields_not_in_view, function(field) {
                return new FormComponent(self, field.name, field.string, field.type);
            });
        }
        $sidebar_content.append(this._render_widgets_components(form_widgets, 'Existing Fields'));
    },
    _append_widgets_many2many_groups: function() {
        var studio_groups = this.attrs.studio_groups ? JSON.parse(this.attrs.studio_groups) : [];
        var record_id = this.datamodel.make_record('ir.model.fields', [{
            name: 'groups',
            relation: 'res.groups',
            relational_value: studio_groups,
            type: 'many2many',
            value: _.pluck(studio_groups, 'id'),
        }]);
        var many2many_options = {
            id_for_label: 'groups',
            mode: 'edit',
            no_quick_create: true,  // FIXME: enable add option
        };
        this.many2many = new Many2ManyTags(this, 'groups', this.datamodel.get(record_id), many2many_options);
        this.many2many.appendTo(this.$('.o_groups'));
    },
    _render_widgets_components: function (form_widgets, category_name) {
        var $components_container = $('<div>').addClass('o_web_studio_field_type_container');
        form_widgets.forEach(function(form_component) {
            form_component.appendTo($components_container);
        });
        return ['<h3>' + category_name + '</h3>', $components_container];
    },
    on_xml_editor: function () {
        this.trigger_up('open_xml_editor');
    },
    on_view_parameters: function() {
        this.trigger_up('open_view_form');
    },
    on_field_parameters: function() {
        this.trigger_up('open_field_form', {field_name: this.node.attrs.name});
    },
    on_defaults: function() {
        this.trigger_up('open_defaults');
    },
    toggle_form_invisible: function(ev) {
        this.show_invisible = !!$(ev.currentTarget).is(":checked");
        this.trigger_up('toggle_form_invisible', {show_invisible : this.show_invisible});
    },
    change_view: function(ev) {
        var $input = $(ev.currentTarget);
        var attribute = $input.attr('name');
        if (attribute) {
            var new_attrs = {};
            if ($input.attr('type') === 'checkbox') {
                if (($input.is(':checked') && !$input.data('inverse')) || (!$input.is(':checked') && $input.data('inverse'))) {
                    new_attrs[attribute] = $input.data('leave-empty') === 'checked' ? '': 'true';
                } else {
                    new_attrs[attribute] = $input.data('leave-empty') === 'unchecked' ? '': 'false';
                }
            } else {
                new_attrs[attribute] = $input.val();
            }
            this.trigger_up('view_change', {
                type: 'attributes',
                structure: 'view_attribute',
                new_attrs: new_attrs,
            });
        }
    },
    change_element: function(ev) {
        var $input = $(ev.currentTarget);
        var attribute = $input.attr('name');
        if (attribute) {
            var new_attrs = {};
            if ($input.attr('type') === 'checkbox') {
                if (!_.contains(["invisible", "required", "readonly"], attribute)) {
                    if ($input.is(':checked')) {
                        new_attrs[attribute] = $input.data('leave-empty') === 'checked' ? '': 'True';
                    } else {
                        new_attrs[attribute] = $input.data('leave-empty') === 'unchecked' ? '': 'False';
                    }
                } else {
                    var newModifiers = _.extend({}, this.modifiers);
                    newModifiers[attribute] = $input.is(':checked');
                    new_attrs = this._get_new_attributes_from_modifiers(newModifiers);
                }
            } else {
                new_attrs[attribute] = $input.val();
            }
            this.trigger_up('view_change', {
                type: 'attributes',
                structure: 'edit_attributes',
                node: this.node,
                new_attrs: new_attrs,
            });
        }
    },
    change_field_group: function() {
        var new_attrs = {};
        new_attrs.groups = this.many2many.value;
        this.trigger_up('view_change', {
            type: 'attributes',
            structure: 'edit_attributes',
            node: this.node,
            new_attrs: new_attrs,
        });
    },
    change_email_alias: function(ev) {
        var $input = $(ev.currentTarget);
        var value = $input.val();
        if (value !== this.email_alias) {
            this.trigger_up('email_alias_change', {
                value: value,
            });
        }
    },
    change_default_value: function(ev) {
        var $input = $(ev.currentTarget);
        var value = $input.val();
        if (value !== this.default_value) {
            this.trigger_up('default_value_change', {
                field_name: this.node.attrs.name,
                value: value,
            });
        }
    },
    remove_element: function() {
        var self = this;
        var message = _.str.sprintf(_t('Are you sure you want to remove this %s from the view?'), this.element);

        Dialog.confirm(this, message, {
            confirm_callback: function() {
                self.trigger_up('view_change', {
                    type: 'remove',
                    structure: 'remove',
                    node: self.node,
                });
                self.toggle_mode('view');
            }
        });
    },
    edit_attrs_domain: function (ev) {
        ev.preventDefault();
        var modifier = ev.currentTarget.dataset.type;

        // Add id to the list of usable fields
        var fields = this.fields_in_view;
        if (!fields.id) {
            fields = _.extend({
                id: {
                    searchable: true,
                    string: "ID",
                    type: "integer",
                },
            }, fields);
        }

        var dialog = new DomainSelectorDialog(this, this.model, _.isArray(this.modifiers[modifier]) ? this.modifiers[modifier] : [], {
            readonly: false,
            fields: fields,
            size: 'medium',
            operators: ["=", "!=", "<", ">", "<=", ">=", "in", "not in", "set", "not set"],
            followRelations: false,
            debugMode: session.debug,
            $content: $(_.str.sprintf(
                _t("<div><p>The <strong>%s</strong> property is only applied to records matching this filter.</p></div>"),
                modifier
            )),
        }).open();
        dialog.on("domain_selected", this, function (e) {
            var newModifiers = _.extend({}, this.modifiers);
            newModifiers[modifier] = e.data.domain;
            var new_attrs = this._get_new_attributes_from_modifiers(newModifiers);
            this.trigger_up('view_change', {
                type: 'attributes',
                structure: 'edit_attributes',
                node: this.node,
                new_attrs: new_attrs,
            });
        });
    },
    open_domain_editor: function (ev) {
        ev.preventDefault();
        var $input = $(ev.currentTarget);

        var dialog = new DomainSelectorDialog(this, this.field_parameters.relation, $input.val(), {
            readonly: false,
            debugMode: session.debug,
        }).open();
        dialog.on("domain_selected", this, function (e) {
            $input.val(domainUtils.domainToString(e.data.domain)).change();
        });
    },
    is_true: function(value) {
        return value !== 'false' && value !== 'False';
    },
    domain_to_str: function (domain) {
        return domainUtils.domainToString(domain);
    },
    _get_new_attributes_from_modifiers: function (modifiers) {
        var newAttributes = {};
        var attrs = [];
        _.each(modifiers, function (value, key) {
            if (value === true || _.isEqual(value, [])) { // modifier always applied, use modifier attribute
                newAttributes[key] = "1";
            } else { // modifier not applied or under certain condition, remove modifier attribute and use attrs if any
                newAttributes[key] = "";
                if (value !== false) {
                    attrs.push(_.str.sprintf("\"%s\": %s", key, domainUtils.domainToString(value)));
                }
            }
        });
        newAttributes.attrs = _.str.sprintf("{%s}", attrs.join(", "));
        return newAttributes;
    }
});

});
