odoo.define('web_studio.NewFieldDialog', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var relational_fields = require('web.relational_fields');
var FieldManagerMixin = require('web.FieldManagerMixin');
var ModelFieldSelector = require("web.ModelFieldSelector");

var _t = core._t;
var Many2one = relational_fields.FieldMany2One;

var NewFieldDialog = Dialog.extend(FieldManagerMixin, {
    template: 'web_studio.NewFieldDialog',

    init: function (parent, model, ttype, fields) {
        this.model = model;
        this.ttype = ttype;
        this.fields = fields;
        var options = {
            title: _t('Add a field'),
            size: 'small',
            buttons: [
                {text: _t("Confirm"), classes: 'btn-primary', click: _.bind(this.save, this)},
                {text: _t("Cancel"), close: true},
            ],
        };
        FieldManagerMixin.init.call(this);
        this._super(parent, options);
    },
    start: function() {
        var record_id;
        var options = {
            mode: 'edit',
        };

        this.$modal.addClass('o_web_studio_field_modal');

        if (this.ttype === 'one2many') {
            record_id = this.datamodel.make_record('ir.model.fields', [{
                name: 'field',
                relation: 'ir.model.fields',
                type: 'many2one',
                domain: [['relation', '=', this.model], ['ttype', '=', 'many2one']],
            }]);
            var record = this.datamodel.get(record_id);
            // it's not possible to create an new many2one field for another model directly from here
            record.fields.field.__attrs.can_create = false;

            this.many2one_field = new Many2one(this, 'field', record, options);
            // TODO: temporary hack, will be fixed with the new views
            this.many2one_field.nodeOptions.no_create_edit = !core.debug;
            this.many2one_field.appendTo(this.$('.o_many2one_field'));
        } else if (_.contains(['many2many', 'many2one'], this.ttype)) {
            record_id = this.datamodel.make_record('ir.model', [{
                name: 'model',
                relation: 'ir.model',
                type: 'many2one',
                domain: [['transient', '=', false], ['abstract', '=', false]]
            }]);
            this.many2one_model = new Many2one(this, 'model', this.datamodel.get(record_id), options);
            // TODO: temporary hack, will be fixed with the new views
            this.many2one_model.nodeOptions.no_create_edit = !core.debug;
            this.many2one_model.appendTo(this.$('.o_many2one_model'));
        } else if (this.ttype === 'related') {
            // This restores default modal height (bootstrap) and allows field selector to overflow
            this.$el.css("overflow", "visible").closest(".modal-dialog").css("height", "auto");
            // We need to get an array of the many2one fields with an attribute 'name'
            // so first we filter to get only the many2one fields
            // then we map to set the attribute 'name'
            // because this.fields have field names as keys and not attribute
            var many2one_fields = _.chain(this.fields)
                .filter(function(f) {return f.type === 'many2one'})
                .map(function(f){f.name = f.key; return f})
                .value();
            var field_options = {
                fields: many2one_fields,
            };
            this.fieldSelector = new ModelFieldSelector(this, this.model, '', field_options);
            return $.when(this.fieldSelector.appendTo(this.$('.o_many2one_field'), this._super.apply(this, arguments)));
        }

        return this._super.apply(this, arguments);
    },
    save: function() {
        var values = {};
        if (this.ttype === 'one2many') {
            values.relation_field_id = this.many2one_field.value;
        } else if (_.contains(['many2many', 'many2one'], this.ttype)) {
            values.relation_id = this.many2one_model.value;
            values.field_description = this.many2one_model.m2o_value;
        } else if (this.ttype === 'selection') {
            var selection_list = _.map(this.$('#selectionItems').val().split("\n"),function(value) {
                value = value.trim();
                if (value) {
                    return "('" + value + "','" + value + "')";
                }
            });
            selection_list = _.reject(_.uniq(selection_list), _.isUndefined.bind());
            values.selection = '[' + selection_list.join() + ']';
        } else if (this.ttype === 'related') {
            values.related = this.fieldSelector.chain;
            values.ttype = this.fieldSelector.selectedField.type;
        }
        this.trigger('field_default_values_saved', values);
    },
});

return NewFieldDialog;

});
