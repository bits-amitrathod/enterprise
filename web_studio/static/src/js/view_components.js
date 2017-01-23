odoo.define('web_studio.view_components', function (require) {
"use strict";

var core = require('web.core');
var Registry = require('web.Registry');
var Widget = require('web.Widget');

var AbstractComponent = Widget.extend({
    structure: false,
    label: false,
    description: false,

    start: function() {
        this.$el.addClass('o_web_studio_component');
        this.$el.data('structure', this.structure);
        this.$el.text(this.label);
        if (core.debug && this.description) {
            this.$el.addClass('o_web_studio_debug');
            this.$el.append($('<div>')
                .addClass('o_web_studio_component_description')
                .text(this.description)
            );
        }
        this.$el.draggable({
            helper: 'clone',
            opacity: 0.4,
            scroll: false,
            revert: 'invalid',
            revertDuration: 200,
            refreshPositions: true,
            start: function(e, ui) {
                $(ui.helper).addClass("ui-draggable-helper");
            }
        });
        return this._super();
    },
});

var NotebookComponent = AbstractComponent.extend({
    structure: 'notebook',
    label: 'Tabs',
    ttype: 'tabs',
    className: 'o_web_studio_field_tabs',
});
var GroupComponent = AbstractComponent.extend({
    structure: 'group',
    label: 'Columns',
    ttype: 'columns',
    className: 'o_web_studio_field_columns',
});
var AbstractNewFieldComponent = AbstractComponent.extend({
    structure: 'field',
    ttype: false,

    start: function() {
        this.description = this.ttype;
        this.$el.data('field_description', {
            ttype: this.ttype,
            field_description: 'New ' + this.label,
        });
        return this._super();
    },
});
var CharFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'char',
    label: 'Text',
    className: 'o_web_studio_field_char',
});
var TextFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'text',
    label: 'Multiline Text',
    className: 'o_web_studio_field_text',
});
var IntegerFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'integer',
    label: 'Integer number',
    className: 'o_web_studio_field_integer',
});
var DecimalFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'float',
    label: 'Decimal Number',
    className: 'o_web_studio_field_float',
});
var HtmlFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'html',
    label: 'Html',
    className: 'o_web_studio_field_html',
});
var MonetaryFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'monetary',
    label: 'Monetary',
    className: 'o_web_studio_field_monetary',
});
var DateFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'date',
    label: 'Date',
    className: 'o_web_studio_field_date',
});
var DatetimeFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'datetime',
    label: 'Date & Time',
    className: 'o_web_studio_field_datetime',
});
var BooleanFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'boolean',
    label: 'Checkbox',
    className: 'o_web_studio_field_boolean',
});
var SelectionFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'selection',
    label: 'Select',
    className: 'o_web_studio_field_selection',
});
var BinaryFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'binary',
    label: 'File',
    className: 'o_web_studio_field_binary',
});

var Many2manyFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'many2many',
    label: 'Many2many',
    className: 'o_web_studio_field_many2many',
});
var One2manyFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'one2many',
    label: 'One2many',
    className: 'o_web_studio_field_one2many',
});
var Many2oneFieldComponent = AbstractNewFieldComponent.extend({
    ttype: 'many2one',
    label: 'Many2one',
    className: 'o_web_studio_field_many2one',
});

var ExistingFieldComponent = AbstractComponent.extend({
    init: function(parent, name, field_description, ttype) {
        this._super(parent);
        this.structure = 'field';
        this.label = field_description;
        this.description = name;
        this.className = 'o_web_studio_field_' + ttype;
    },

    start: function() {
        this.$el.data('new_attrs',{
            name: this.description,
        });
        return this._super();
    },
});

var AbstractNewWidgetComponent = AbstractNewFieldComponent.extend({
    attrs: {},

    start: function() {
        this.$el.data('new_attrs', this.attrs);
        return this._super();
    },
});
var ImageWidgetComponent = AbstractNewWidgetComponent.extend({
    ttype: 'binary',
    label: 'Image',
    className: 'o_web_studio_field_picture',
    attrs: {widget: 'image'},
});
var TagWidgetComponent = AbstractNewWidgetComponent.extend({
    ttype: 'many2many',
    label: 'Tags',
    className: 'o_web_studio_field_tags',
    attrs: {widget: 'many2many_tags'},
});
var PriorityWidgetComponent = AbstractNewWidgetComponent.extend({
    ttype: 'selection',
    label: 'Priority',
    className: 'o_web_studio_field_priority',
    attrs: {widget: 'priority'},
});
var form_component_widget_registry = new Registry();
form_component_widget_registry
    .add('form_components', [
        NotebookComponent,
        GroupComponent,
    ])
    .add('new_field', [
        CharFieldComponent,
        TextFieldComponent,
        IntegerFieldComponent,
        DecimalFieldComponent,
        HtmlFieldComponent,
        MonetaryFieldComponent,
        DateFieldComponent,
        DatetimeFieldComponent,
        BooleanFieldComponent,
        SelectionFieldComponent,
        BinaryFieldComponent,
        One2manyFieldComponent,
        Many2oneFieldComponent,
        Many2manyFieldComponent,
        ImageWidgetComponent,
        TagWidgetComponent,
        PriorityWidgetComponent,
    ])
    .add('existing_field', ExistingFieldComponent);

return {
    registry: form_component_widget_registry,
};

});
