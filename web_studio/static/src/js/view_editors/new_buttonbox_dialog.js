odoo.define('web_studio.NewButtonBoxDialog', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var relational_fields = require('web.relational_fields');

var FieldManagerMixin = require('web_studio.FieldManagerMixin');
var utils = require('web_studio.utils');

var _t = core._t;

var NewButtonBoxDialog = Dialog.extend(FieldManagerMixin, {
    template: 'web_studio.NewButtonBoxDialog',

    events: {
        'click .o_web_studio_icon_selector': 'on_icon_clicked',
    },

    init: function(parent, model) {
        FieldManagerMixin.init.call(this);
        this.model = model;
        this.ICONS = utils.ICONS;

        var options = {
            title: _t('Add a Button'),
            size: 'small',
            buttons: [
                {text: _t("Confirm"), classes: 'btn-primary', click: _.bind(this.save, this)},
                {text: _t("Cancel"), close: true},
            ],
        };

        this._super(parent, options);

        var self = this;
        this.opened().then(function () {
            // focus on input
            self.$el.find('input[name="string"]').focus();
        });
    },
    start: function() {
        var record_id_many2one = this.datamodel.make_record('ir.actions.act_window', [{
            name: 'field',
            relation: 'ir.model.fields',
            type: 'many2one',
            domain: [['relation', '=', this.model], ['ttype', '=', 'many2one'], ['store', '=', true]],
        }]);
        var options = {
            mode: 'edit',
            no_quick_create: true,
        };
        var Many2one = relational_fields.FieldMany2One;
        this.many2one = new Many2one(this, 'field', this.datamodel.get(record_id_many2one), options);
        this.many2one.appendTo(this.$('.js_many2one_field'));
        return this._super.apply(this, arguments);
    },
    on_icon_clicked: function(event) {
        var $el = $(event.currentTarget);
        this.$('.o_selected').removeClass('o_selected');
        $el.addClass('o_selected');
        var icon = $(event.currentTarget).data('value');
        // only takes `fa-...` instead of `fa fa-...`
        this.selected_icon = icon && icon.split(' ')[1];
    },
    save: function() {
        var string = this.$('input[name="string"]').val() || 'New Button';
        var icon = this.selected_icon || this.ICONS[0].split(' ')[1];
        var field_id = this.many2one.value;
        if (!field_id) {
            Dialog.alert(this, _t('Select a related field.'));
            return;
        }
        this.trigger('saved', {
            string: string,
            field_id: field_id,
            icon: icon,
        });
        this.close();
    },
});

return NewButtonBoxDialog;

});
