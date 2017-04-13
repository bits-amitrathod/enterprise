odoo.define('web_studio.ActionEditorView', function (require) {
"use strict";

var Widget = require('web.Widget');

var ActionEditorView = Widget.extend({
    template: 'web_studio.ActionEditorView',

    events: {
        'click .dropdown-menu > li > a': function (event) {
            event.preventDefault();
            var action = $(event.currentTarget).data('action');
            this[action](event);
        },
        'click .o_web_studio_thumbnail': 'on_click_thumbnail',
    },

    init: function (parent, flags) {
        this._super.apply(this, arguments);

        this.active = flags.active;
        this.default_view = flags.default_view;
        this.type = flags.type;
        this.can_default = flags.can_default;
        this.can_set_another = flags.can_set_another;
        this.can_be_disabled = flags.can_be_disabled;
    },

    on_click_thumbnail: function () {
       if (this.active) {
            this.trigger_up('studio_edit_view', {view_type: this.type});
        } else {
            this.trigger_up('studio_new_view', {view_type: this.type});
        }
    },

    set_default_view: function (event) {
        this.trigger_up('studio_default_view', {view_type: this.type});
    },

    set_another_view: function () {
        this.trigger_up('studio_set_another_view', {view_mode: this.type});
    },

    disable_view: function () {
        this.trigger_up('studio_disable_view', {view_type: this.type});
    },
});

return ActionEditorView;

});
