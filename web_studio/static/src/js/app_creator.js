odoo.define('web_studio.AppCreator', function (require) {
"use strict";

var core = require('web.core');
var framework = require('web.framework');
var Widget = require('web.Widget');
var relational_fields = require('web.relational_fields');

var customize = require('web_studio.customize');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var IconCreator = require('web_studio.IconCreator');

var QWeb = core.qweb;
var FieldMany2One = relational_fields.FieldMany2One;
var _t = core._t;

var AppCreator = Widget.extend(StandaloneFieldManagerMixin, {
    template: 'web_studio.AppCreator',
    events: {
        'click .o_web_studio_app_creator_next': '_onNext',
        'click .o_web_studio_app_creator_back': '_onBack',
        'change input': '_onCheckFields',
        'keyup input': '_onCheckFields',
        'input input': '_onCheckFields',
        'paste input': '_onCheckFields',
        'focus input.o_web_studio_app_creator_field_warning': '_onInput',
        'keyup input.o_web_studio_app_creator_field_warning': '_onInput',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.currentStep = 1;
        this.debug = core.debug;
    },
    /**
     * @override
     */
    start: function () {
        this._update();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Re-render the widget and update its content according to @currentStep
     */
    update: function () {
        this.renderElement();
        this._update();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /*
     * Check that all the fields in the form are correctly filled, according to
     * the @currentStep. If one isn't, this is emphasized by ´_fieldWarning´.
     */
    _checkFields: function (field_warning) {
        var ready = false;
        var warningClass = 'o_web_studio_app_creator_field_warning';

        if (this.currentStep === 2) {
            var app_name = this.$('input[name="app_name"]').val();
            if (app_name) {
                ready = true;
                this.$next.find('span').text(_t('Next'));
            } else if (field_warning) {
                this.$next.find('span').empty();
                this.$('.o_web_studio_app_creator_name').addClass(warningClass);
            }
        } else if (this.currentStep === 3) {
            var menu_name = this.$('input[name="menu_name"]').val();
            if (field_warning && !menu_name) {
                this.$('.o_web_studio_app_creator_menu').addClass(warningClass);
            }
            var model_id = this.many2one.value;
            var model_choice = this.$('input[name="model_choice"]').is(':checked');

            if (field_warning && model_choice && !model_id) {
                this.$('.o_web_studio_app_creator_model').addClass(warningClass);
            }

            this.$next.find('span').empty();
            if (menu_name) {
                // we can only select a model in debug mode
                if (!this.debug || !model_choice || (model_choice && model_id)) {
                    ready = true;
                    this.$next.find('span').text(_t('Create your app'));
                }
            }
            this.$('.o_web_studio_app_creator_model').toggle(model_choice);
        }

        this.$next.toggleClass('is_ready', ready);
        return ready;
    },
    /*
     * Update the widget according to the @currentStep
     * The steps are:
     *   1) welcome
     *   2) form with the app name
     *   3) form with the menu name and an optional model
     */
    _update: function () {
        this.$left = this.$('.o_web_studio_app_creator_left_content');
        this.$right = this.$('.o_web_studio_app_creator_right_content');
        this.$back = this.$('.o_web_studio_app_creator_back');
        this.$next = this.$('.o_web_studio_app_creator_next');

        // hide back button for step 1)
        this.$back.toggleClass('o_hidden', (this.currentStep === 1));

        this.$next.removeClass('is_ready');

        if (this.currentStep === 1) {
            // add 'Welcome to' content
            var $welcome = $(QWeb.render('web_studio.AppCreator.Welcome'));
            this.$left.append($welcome);
            this.$right.append($('<img>', {
                src: "/web_studio/static/src/img/studio_app_icon.png",
                class: 'o_web_studio_welcome_image',
            }));

            // manage 'previous' and 'next' buttons
            this.$back.addClass('o_hidden');
            this.$next.find('span').text(_t('Next'));
            this.$next.addClass('is_ready');
        } else if (this.currentStep === 2) {
            // add 'Create your App' content
            var $appForm = $(QWeb.render('web_studio.AppCreator.App', {
                widget: this,
            }));
            this.$left.append($appForm);

            if (!this.iconCreator) {
                this.iconCreator = new IconCreator(this, 'edit');
            } else {
                this.iconCreator.enable_edit();
            }
            this.iconCreator.appendTo(this.$right);

            // focus on input
            this.$('input[name="app_name"]').focus();

            // toggle button if the form is ready
            this.$('input').on('change keyup input paste', this._onCheckFields.bind(this));
            this._checkFields();
        } else {
            // create a Many2one field widget for the custom model
            var recordID = this.model.makeRecord('ir.actions.act_window', [{
                name: 'model',
                relation: 'ir.model',
                type: 'many2one',
                domain: [['transient', '=', false], ['abstract', '=', false]]
            }]);
            var record = this.model.get(recordID);
            var options = {
                mode: 'edit',
            };
            this.many2one = new FieldMany2One(this, 'model', record, options);
            this._registerWidget(recordID, 'model', this.many2one);

            // add 'Create your first Menu' content
            var $menuForm= $(QWeb.render('web_studio.AppCreator.Menu', {
                widget: this,
            }));
            this.many2one.appendTo($menuForm.find('.js_model'));
            this.$left.append($menuForm);
            this.iconCreator.disable_edit();
            this.iconCreator.appendTo(this.$right);

            // focus on input
            this.$('input[name="app_name"]').focus();

            // toggle button if the form is ready
            this.$('input').on('change keyup input paste', this._onCheckFields.bind(this));
            this._checkFields();
        }

        // focus on input
        this.$('input').focus();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onBack: function () {
        this.currentStep--;
        this.update();
    },
    _onCheckFields: function () {
        this._checkFields(false);
    },
    /*
     * @private
     *
     * Overwrite the method of the StandaloneFieldManagerMixin to call ´_checkFields´ each
     * time the field widget changes.
     */
    _onFieldChanged: function () {
        StandaloneFieldManagerMixin._onFieldChanged.apply(this, arguments);
        this._checkFields(false);
    },
    /**
     * @private
     *
     * @param {Event} e
     */
    _onInput: function (e) {
        $(e.currentTarget).removeClass('o_web_studio_app_creator_field_warning');
    },
    /**
     * @private
     */
    _onNext: function () {
        if (this.currentStep === 1) {
            this.currentStep++;
            this.update();
        } else if (this.currentStep === 2) {
            if (!this._checkFields(true)) { return; }

            // everything is fine, let's save the values before the next step
            this.app_name = this.$('input[name="app_name"]').val();
            this.icon = this.iconCreator.get_value();
            this.currentStep++;
            this.update();
        } else {
            if (!this._checkFields(true)) { return; }
            var menu_name = this.$('input[name="menu_name"]').val();
            var model_choice = this.$('input[name="model_choice"]').is(':checked');
            var model_id = model_choice && this.many2one.value;

            framework.blockUI();
            customize
                .create_new_app(this.app_name, menu_name, model_id.res_id, this.icon)
                .then(this.trigger_up.bind(this, 'new_app_created'))
                .always(framework.unblockUI.bind(framework));
        }
    },
});

core.action_registry.add('action_web_studio_app_creator', AppCreator);

return AppCreator;

});
