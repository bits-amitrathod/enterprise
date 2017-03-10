odoo.define('web_studio.AppCreator', function (require) {
"use strict";

var core = require('web.core');
var framework = require('web.framework');
var Widget = require('web.Widget');
var relational_fields = require('web.relational_fields');

var customize = require('web_studio.customize');
var FieldManagerMixin = require('web_studio.FieldManagerMixin');
var IconCreator = require('web_studio.IconCreator');

var QWeb = core.qweb;
var _t = core._t;

var AppCreator = Widget.extend(FieldManagerMixin, {
    template: 'web_studio.AppCreator',
    events: {
        'click .o_web_studio_app_creator_next': 'on_next',
        'click .o_app_creator_back': 'on_back',
    },
    custom_events: _.extend({}, FieldManagerMixin.custom_events, {
        'field_changed': '_on_check_menu_fields',
    }),

    init: function () {
        this.current_step = 1;
        FieldManagerMixin.init.call(this);
        this._super.apply(this, arguments);
        this.debug = core.debug;
    },
    start: function () {
        this._update();
        return this._super.apply(this, arguments);
    },

    on_next: function () {
        var self = this;

        if (this.current_step === 1) {
            this.current_step++;
            this.update();
        } else if (this.current_step === 2) {
            if (!this._check_app_fields(true)) { return; }

            // everything is fine, let's save the values before the next step
            this.app_name = this.$('input[name="app_name"]').val();
            this.icon = this.icon_creator.get_value();
            this.current_step++;
            this.update();
        } else {
            if (!this._check_menu_fields(true)) { return; }
            var menu_name = this.$('input[name="menu_name"]').val();
            var model_choice = this.$('input[name="model_choice"]').is(':checked');
            var model_id = model_choice && this.many2one.value;

            framework.blockUI();
            customize.create_new_app(this.app_name, menu_name, model_id, this.icon)
                .then(function(result) {
                    self.trigger_up('new_app_created', result);
                })
                .always(function() {
                    framework.unblockUI();
                });
        }
    },

    on_back: function () {
        this.current_step--;
        this.update();
    },

    _on_check_app_fields: function () {
        this._check_app_fields(false);
    },
    _on_check_menu_fields: function () {
        this._check_menu_fields(false);
    },
    _check_app_fields: function(field_warning) {
        // Validate fields
        var app_name = this.$('input[name="app_name"]').val();
        var ready = true;
        if (!app_name) {
            ready = false;
            this.$next.find('span').empty();
            if (field_warning) {
                this.field_warning(this.$('.o_web_studio_app_creator_name'));
            }
        } else {
            this.$next.find('span').text(_t('Next'));
        }
        this.$next.toggleClass('is_ready', ready);

        return app_name;
    },
    _check_menu_fields: function (field_warning) {
        // Validate fields
        var menu_name = this.$('input[name="menu_name"]').val();
        if (field_warning && !menu_name) {
            this.field_warning(this.$('.o_web_studio_app_creator_menu'));
        }
        var model_id = this.many2one.value;
        var model_choice = this.$('input[name="model_choice"]').is(':checked');

        if (field_warning && model_choice && !model_id) {
            this.field_warning(this.$('.o_web_studio_app_creator_model'));
        }

        var ready = false;
        this.$next.find('span').empty();
        if (menu_name && (!this.debug || !model_choice || (model_choice && model_id))) {
            ready = true;
            this.$next.find('span').text(_t('Create your app'));
        }
        this.$next.toggleClass('is_ready', ready);
        this.$('.o_web_studio_app_creator_model').toggle(model_choice);

        return ready;
    },

    field_warning: function($el) {
        $el.addClass('o_web_studio_app_creator_field_warning');
        $el.find('input').on('focus keyup', function() {
            $el.removeClass('o_web_studio_app_creator_field_warning');
        });
    },
    update: function () {
        this.renderElement();
        this._update();
    },
    _update: function () {
        this.$left = this.$('.o_web_studio_app_creator_left_content');
        this.$right = this.$('.o_web_studio_app_creator_right_content');
        this.$next = this.$('.o_web_studio_app_creator_next');

        if (this.current_step === 1) {
            // add 'Welcome to' content
            this.$left.append($(QWeb.render('web_studio.AppCreator.Welcome')));
            this.$right.append($('<img>', {
                src: "/web_studio/static/src/img/studio_app_icon.png"
            }).addClass('o_web_studio_welcome_image'));

            // manage 'previous' and 'next' buttons
            this.$('.o_app_creator_back').addClass('o_hidden');
            this.$next.find('span').text(_t('Next'));
            this.$next.addClass('is_ready');
        } else if (this.current_step === 2) {
            // add 'Create your App' content
            this.$left.append($(QWeb.render('web_studio.AppCreator.Form', {widget: this})));
            if (!this.icon_creator) {
                this.icon_creator = new IconCreator(this, 'edit');
            } else {
                this.icon_creator.enable_edit();
            }
            this.icon_creator.appendTo(this.$right);

            // focus on input
            this.$('input[name="app_name"]').focus();

            // toggle button if the form is ready
            this.$('input').on('change keyup input paste', this._on_check_app_fields.bind(this));
            this._check_app_fields();
        } else {
            // add 'Create your first Menu' content
            var $menu_form= $(QWeb.render('web_studio.AppCreator.Menu', {widget: this}));

            var record_id = this.datamodel.make_record('ir.actions.act_window', [{
                name: 'model',
                relation: 'ir.model',
                type: 'many2one',
                domain: [['transient', '=', false], ['abstract', '=', false]]
            }]);
            var options = {
                mode: 'edit',
            };
            var Many2one = relational_fields.FieldMany2One;
            this.many2one = new Many2one(this, 'model', this.datamodel.get(record_id), options);
            this.many2one.appendTo($menu_form.find('.js_model'));

            this.$left.append($menu_form);
            this.icon_creator.disable_edit();
            this.icon_creator.appendTo(this.$right);

            // focus on input
            this.$('input[name="menu_name"]').focus();

            // toggle button if the form is ready
            this.$('input').on('change keyup input paste', this._on_check_menu_fields.bind(this));
            this._check_menu_fields();
        }
    },
});

core.action_registry.add('action_web_studio_app_creator', AppCreator);

});
