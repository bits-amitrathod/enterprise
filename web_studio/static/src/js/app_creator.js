odoo.define('web_studio.AppCreator', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var relational_fields = require('web.relational_fields');

var customize = require('web_studio.customize');
var FieldManagerMixin = require('web_studio.FieldManagerMixin');
var IconCreator = require('web_studio.IconCreator');

var QWeb = core.qweb;

var AppCreator = Widget.extend(FieldManagerMixin, {
    template: 'web_studio.AppCreator',
    events: {
        'click .o_web_studio_app_creator_next': 'on_next',
        'click .o_app_creator_back': 'on_back',
    },
    custom_events: _.extend({}, FieldManagerMixin.custom_events, {
        'field_changed': '_check_fields',
    }),

    init: function () {
        this.current_step = 1;
        FieldManagerMixin.init.call(this);
        this._super.apply(this, arguments);
    },
    start: function () {
        this.$left = this.$('.o_web_studio_app_creator_left_content');
        this.$right = this.$('.o_web_studio_app_creator_right_content');
        this.update();
        return this._super.apply(this, arguments);
    },

    on_next: function () {
        var self = this;

        if (this.current_step === 1) {
            this.current_step++;
            this.update();
        } else {
            if (!this._check_fields()) { return; }

            // everything is fine, let's create the App
            var name = this.$('input[name="app_name"]').val();
            var icon = this.icon_creator.get_value();
            var model_choice = this.$('input[name="model_choice"]').is(':checked');
            var model_id = model_choice && this.many2one.value;

            customize.create_new_app(name, model_id, icon).then(function(result) {
                self.trigger_up('new_app_created', result);
            });
        }
    },

    on_back: function () {
        this.current_step--;
        this.update();
    },

    _check_fields: function () {
        var name = this.$('input[name="app_name"]').val();
        var model_id = this.many2one.value;
        var model_choice = this.$('input[name="model_choice"]').is(':checked');

        // Validate fields
        if (!name) {
            this.field_warning(this.$('.o_web_studio_app_creator_name'));
        }

        if (model_choice && !model_id) {
            this.field_warning(this.$('.o_web_studio_app_creator_model'));
        }

        var ready = false;
        if (name && (!model_choice || (model_choice && model_id))) {
            ready = true;
        }
        this.$('.o_web_studio_app_creator_next').toggleClass('is_ready', ready);
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
        this.$left.empty();
        this.$right.empty();

        var $next = this.$('.o_web_studio_app_creator_next');

        if (this.current_step === 1) {
            $next.text('Next');

            this.$left.append($(QWeb.render('web_studio.AppCreator.Welcome')));

            this.$right.append($('<img>', {
                src: "/web_studio/static/src/img/studio_app_icon.png"
            }).addClass('o_web_studio_welcome_image'));
        } else {
            $next.empty()
                .append($('<span>').text('Create your app'))
                .append($('<i>', {class: 'fa fa-chevron-right'}));

            var $app_form= $(QWeb.render('web_studio.AppCreator.Form'));

            var record_id = this.datamodel.make_record('ir.actions.act_window', [{
                name: 'model',
                relation: 'ir.model',
                type: 'many2one',
                domain: [['transient', '=', false], ['abstract', '=', false]]
            }]);
            var options = {
                mode: 'edit',
                no_quick_create: true,  // FIXME: enable add option
            };
            var Many2one = relational_fields.FieldMany2One;
            this.many2one = new Many2one(this, 'model', this.datamodel.get(record_id), options);
            this.many2one.appendTo($app_form.find('.js_model'));

            this.$left.append($app_form);

            // focus on input
            this.$('input[name="name"]').focus();

            // toggle button if the form is ready
            this.$('input').on('change keyup input paste', _.bind(this._check_fields, this));

            this.icon_creator = new IconCreator(this);
            this.icon_creator.appendTo(this.$right);
        }

        this.$('.o_app_creator_back').toggleClass('o_hidden', (this.current_step === 1));
        $next.toggleClass('o_web_studio_create', (this.current_step === 2));
    }
});

core.action_registry.add('action_web_studio_app_creator', AppCreator);

});
