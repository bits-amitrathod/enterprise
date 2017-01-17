odoo.define('web_studio.SubMenu', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');

var bus = require('web_studio.bus');

var _t = core._t;

var SubMenu = Widget.extend({
    template: 'web_studio.Menu',
    events: {
        'click .o_menu_sections a': 'on_menu_click',
        'click .o_web_studio_undo': 'on_undo',
        'click .o_web_studio_redo': 'on_redo',
    },

    init: function(parent, action, active_view, options) {
        var self = this;

        this._super.apply(this, arguments);
        this.action = action;
        this.studio_actions = [{action: 'action_web_studio_main', title: 'Views'}];
        this.multi_lang = options.multi_lang;
        if (active_view) { this.add_breadcrumb_view_type(active_view); }

        bus.on('action_changed', this, function(new_action) { self.action = new_action; });

        bus.on('undo_available', this, this.toggle_undo.bind(this, true));
        bus.on('undo_not_available', this, this.toggle_undo.bind(this, false));
        bus.on('redo_available', this, this.toggle_redo.bind(this, true));
        bus.on('redo_not_available', this, this.toggle_redo.bind(this, false));

        bus.on('edition_mode_entered', this, function(view_type) {
            this.$('.o_menu_sections li a.active').removeClass('active');
            self.add_breadcrumb_view_type(view_type);
            self.render_breadcrumb();
        });
    },

    start: function() {
        var self = this;
        this._super.apply(this, arguments).then(function() {
            self.render_breadcrumb();
        });
    },

    on_menu_click: function(ev) {
        var $menu = $(ev.currentTarget);
        if (!$menu.data('name')) { return; }

        // make the primary menu active
        this.$('.active').removeClass('active');
        $menu.addClass('active');

        // do the corresponding action
        var title = $menu.text();
        if ($menu.data('name') === 'views') {
            return this.replace_action('action_web_studio_main', title, {
                action: this.action,
                clear_breadcrumbs: true,
                disable_edition: true,
            });
        } else {
            var self = this;
            return ajax.jsonRpc('/web_studio/get_studio_action', 'call', {
                action_name: $menu.data('name'),
                model: this.action.res_model,
                view_id: this.action.view_id[0],
            }).then(function (result) {
                result.keep_state = true;
                return self.replace_action(result, title, {
                    clear_breadcrumbs: true,
                    disable_edition: true,
                });
            });
        }
    },
    add_breadcrumb_view_type: function(view_type) {
        if (this.studio_actions.length === 1) {
            this.studio_actions.push({title: view_type.charAt(0).toUpperCase() + view_type.slice(1)});
        }
    },
    replace_action: function(action, title, options) {
        this.studio_actions = [{action: action, title: title}];
        this.do_action(action, options);
        this.render_breadcrumb();
    },
    on_undo: function() {
        bus.trigger('undo_clicked');
    },

    on_redo: function() {
        bus.trigger('redo_clicked');
    },
    toggle_undo: function(display) {
        this.$('.o_web_studio_undo').toggleClass('o_web_studio_active', display);
    },
    toggle_redo: function(display) {
        this.$('.o_web_studio_redo').toggleClass('o_web_studio_active', display);
    },
    render_breadcrumb: function () {
        var self = this;
        var $breadcrumb = $('<ol>').addClass('breadcrumb');
        _.each(this.studio_actions, function (bc, index) {
            $breadcrumb.append(self._render_breadcrumbs_li(bc, index, self.studio_actions.length));
        });
        this.$('.o_web_studio_breadcrumb')
            .empty()
            .append($breadcrumb);
    },
    _render_breadcrumbs_li: function (bc, index, length) {
        var self = this;
        var is_last = (index === length-1);
        var is_before_last = (index === length-2);
        var li_content = bc.title && _.escape(bc.title.trim());
        var $bc = $('<li>')
            .append(li_content)
            .toggleClass('active', is_last);
        if (!is_last) {
            $bc.click(function () {
                self.replace_action(bc.action, bc.title, {
                    action: self.action,
                    clear_breadcrumbs: true,
                    disable_edition: true,
                });
            });
        }
        if (is_before_last) {
            $bc.toggleClass('o_back_button');
        }
        return $bc;
    },
});

return SubMenu;

});
