odoo.define('web_studio.EditMenu', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var FieldManagerMixin = require('web.FieldManagerMixin');
var form_common = require('web.view_dialogs');
var relational_fields = require('web.relational_fields');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var Widget = require('web.Widget');

var customize = require('web_studio.customize');

var _t = core._t;
var Many2One = relational_fields.FieldMany2One;

var EditMenu = Widget.extend({
    template: 'web_studio.EditMenu',
    events: {
        'click .o_web_edit_menu': 'on_click',
    },

    init: function(parent, menu_data, current_primary_menu) {
        this._super.apply(this, arguments);
        this.menu_data = menu_data;
        this.current_primary_menu = current_primary_menu;
    },

    on_click: function (event) {
        event.preventDefault();
        new EditMenuDialog(this, this.menu_data, this.current_primary_menu).open();
    },
});

var EditMenuDialog = Dialog.extend({
    template: 'web_studio.EditMenu_wizard',
    events: _.extend({}, Dialog.prototype.events, {
        'click a.js_add_menu': 'add_menu',
        'click button.js_edit_menu': 'edit_menu',
        'click button.js_delete_menu': 'delete_menu',
    }),

    init: function(parent, menu_data, current_primary_menu) {
        var options = {
            title: _t('Edit Menu'),
            size: 'medium',
            dialogClass: 'o_web_studio_edit_menu_modal',
            buttons: [
                {text: _t("Confirm"), classes: 'btn-primary', click: _.bind(this.save, this)},
                {text: _t("Cancel"), close: true},
            ],
        };
        this.current_primary_menu = current_primary_menu;
        this.roots = this.get_menu_data_filtered(menu_data);

        this.to_delete = [];
        this.to_move = {};

        this._super(parent, options);
    },

    start: function () {
        var self = this;

        this.$('.oe_menu_editor').nestedSortable({
            listType: 'ul',
            handle: 'div',
            items: 'li',
            maxLevels: 5,
            toleranceElement: '> div',
            forcePlaceholderSize: true,
            opacity: 0.6,
            placeholder: 'oe_menu_placeholder',
            tolerance: 'pointer',
            attribute: 'data-menu-id',
            expression: '()(.+)', // nestedSortable takes the second match of an expression (*sigh*)
            relocate: this.move_menu.bind(this),
        });

        return this._super.apply(this, arguments);
    },

    get_menu_data_filtered: function(menu_data) {
        var self = this;
        var menus = menu_data.children.filter(function (el) {
            return el.id === self.current_primary_menu;
        });
        return menus;
    },

    add_menu: function (ev) {
        ev.preventDefault();

        var self = this;
        var form = new NewMenuDialog(this, this.current_primary_menu).open();
        form.on('record_saved', self, function() {
            self._reload_menu_data(true);
        });
    },

    delete_menu: function (ev) {
        var $menu = $(ev.currentTarget).closest('[data-menu-id]');
        var menu_id = $menu.data('menu-id') || 0;
        if (menu_id) {
            this.to_delete.push(menu_id);
        }
        $menu.remove();
    },

    edit_menu: function (ev) {
        var menu_id = $(ev.currentTarget).closest('[data-menu-id]').data('menu-id');
        var form = new form_common.FormViewDialog(this, {
            res_model: 'ir.ui.menu',
            res_id: menu_id,
        }).open();

        form.on('record_saved', this, function() {
            this._reload_menu_data(true);
        });
    },

    move_menu: function (ev) {
        var self = this;

        var $menu = $(ev.toElement).closest('[data-menu-id]');
        var menu_id = $menu.data('menu-id');

        this.to_move[menu_id] = {
            parent_id: $menu.parents('[data-menu-id]').data('menu-id') || this.current_primary_menu,
            sequence: $menu.index(),
        };

        // Resequence siblings
        _.each($menu.siblings('li'), function(el) {
            var menu_id = $(el).data('menu-id');
            if (menu_id in self.to_move) {
                self.to_move[menu_id].sequence = $(el).index();
            } else {
                self.to_move[menu_id] = {sequence: $(el).index()};
            }
        });
    },

    save: function () {
        var self = this;
        return this.performModelRPC('ir.ui.menu', 'customize', [], {to_move: this.to_move, to_delete: this.to_delete})
            .then(function(){
                self._reload_menu_data();
                self.close();
            });
    },

    _reload_menu_data: function(keep_open) {
        this.trigger_up('reload_menu_data', {keep_open: keep_open});
    },
});

// The Many2One field is extended to catch when a model is quick created
// to avoid letting the user click on the save menu button
// before the model is created.
var EditMenuMany2One = Many2One.extend({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _quickCreate: function () {
        this.trigger_up('edit_menu_disable_save');
        var def = this._super.apply(this, arguments);
        $.when(def).always(this.trigger_up.bind(this, 'edit_menu_enable_save'));

    },
});

var NewMenuDialog = Dialog.extend(StandaloneFieldManagerMixin, {
    template: 'web_studio.EditMenu_new',
    custom_events: _.extend({}, Dialog.prototype.custom_events, FieldManagerMixin.custom_events, {
        edit_menu_disable_save: function () {
            this.$footer.find('.confirm_button').attr("disabled", "disabled");
        },
        edit_menu_enable_save: function () {
            this.$footer.find('.confirm_button').removeAttr("disabled");
        },
    }),

    init: function(parent, parent_id) {
        this.parent_id = parent_id;
        var options = {
            title: _t('Create a new Menu'),
            size: 'small',
            buttons: [{
                text: _t("Confirm"),
                classes: 'btn-primary confirm_button',
                click: _.bind(this.save, this),
            }, {
                text: _t("Cancel"),
                close: true,
            }],
        };
        this._super(parent, options);
        StandaloneFieldManagerMixin.init.call(this);
    },
    start: function() {
        var self = this;

        this.opened().then(function () {
            self.$modal.addClass('o_web_studio_add_menu_modal');
            // focus on input
            self.$el.find('input[name="name"]').focus();
        });

        return this._super.apply(this, arguments).then(function() {
            var record_id = self.model.makeRecord('ir.actions.act_window', [{
                name: 'model',
                relation: 'ir.model',
                type: 'many2one',
                domain: [['transient', '=', false], ['abstract', '=', false]],
            }]);
            var options = {
                mode: 'edit',
            };
            self.many2one = new EditMenuMany2One(self, 'model', self.datamodel.get(record_id), options);
            // TODO: temporary hack, will be fixed with the new views
            self.many2one.nodeOptions.no_create_edit = !core.debug;
            self.many2one.appendTo(self.$('.js_model'));
        });
    },
    save: function() {
        var self = this;

        var name = this.$el.find('input').first().val();
        var model_id = this.many2one.value;

        return customize.create_new_menu(name, this.parent_id, model_id).then(function(){
                self.trigger('record_saved');
                self.close();
            });
    },


});

return EditMenu;

});
