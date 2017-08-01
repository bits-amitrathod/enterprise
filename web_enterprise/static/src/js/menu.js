odoo.define('web_enterprise.Menu', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var Widget = require('web.Widget');
var SystrayMenu = require('web.SystrayMenu');
var UserMenu = require('web.UserMenu');

UserMenu.prototype.sequence = 0; // force UserMenu to be the right-most item in the systray
SystrayMenu.Items.push(UserMenu);

var QWeb = core.qweb;

/**
 * Usermenu for mobile.
 **/
var UserMenuMobile = UserMenu.extend({
    template: 'UserMenu.Mobile',
     events: _.extend({}, UserMenu.prototype.events, {
        'click li a[data-menu]': '_onUserMenuClick',
     }),

     // Handlers
    /**
     * On Usermenu click call particular method.
     * @private
     */
     _onUserMenuClick: function (ev) {
        var menu = $(ev.target).data('menu');
        this['_onMenu' + menu.charAt(0).toUpperCase() + menu.slice(1)]();
     }
});

var Menu = Widget.extend({
    template: 'Menu',
    events: {
        'click .o_menu_toggle': function (ev) {
            ev.preventDefault();
            this.trigger_up((this.appswitcher_displayed)? 'hide_app_switcher' : 'show_app_switcher');
            this.$el.parent().removeClass('o_mobile_menu_opened');
        },
        'mouseover .o_menu_sections > li:not(.open)': function(e) {
            if (config.device.size_class >= config.device.SIZES.SM) {
                var $opened = this.$('.o_menu_sections > li.open');
                if($opened.length) {
                    $opened.removeClass('open');
                    $(e.currentTarget).addClass('open').find('> a').focus();
                }
            }
        },
        'click .o_menu_brand': '_onMainMenuClick',
        'click .o_mobile_menu_toggle': '_onBurgerMenuToggleClick',
        'click .o_mobile_menu_close': '_onBurgerMenuCloseClick'
    },
    init: function (parent, menu_data) {
        var self = this;
        this._super.apply(this, arguments);
        this.appswitcher_displayed = true;
        this.backbutton_displayed = false;

        this.$menu_sections = {};
        this.menu_data = menu_data;

        // Prepare navbar's menus
        var $menu_sections = $(QWeb.render('Menu.sections', {'menu_data': this.menu_data}));
        $menu_sections.filter('section').each(function () {
            self.$menu_sections[parseInt(this.className, 10)] = $(this).children('li');
        });

        // Bus event
        core.bus.on('change_menu_section', this, this.change_menu_section);
        core.bus.on('toggle_mode', this, this.toggle_mode);
    },
    start: function () {
        var self = this;

        this.$menu_toggle = this.$('.o_menu_toggle');
        this.$menu_brand_placeholder = this.$('.o_menu_brand');
        this.$section_placeholder = this.$('.o_menu_sections');

        // Navbar's menus event handlers
        var on_secondary_menu_click = function (ev) {
            ev.preventDefault();
            var menu_id = $(ev.currentTarget).data('menu');
            var action_id = $(ev.currentTarget).data('action-id');
            self._on_secondary_menu_click(menu_id, action_id);
        };
        var menu_ids = _.keys(this.$menu_sections);
        var primary_menu_id, $section;
        for(var i = 0; i < menu_ids.length; i++) {
            primary_menu_id = menu_ids[i];
            $section = this.$menu_sections[primary_menu_id];
            $section.on('click', 'a[data-menu]', self, on_secondary_menu_click.bind(this));
        }

        // Systray Menu
        this.systray_menu = new SystrayMenu(this);
        this.systray_menu.attachTo(this.$('.o_menu_systray'));

        core.bus.on("resize", this, _.debounce(this._handle_extra_items, 500));

        // Hide usermenu and switch company menu in mobile view becuase we have added new burger menu for both
        this.$('.o_user_menu, .o_switch_company_menu').addClass('hidden-xs');

        return this._super.apply(this, arguments);
    },
    toggle_mode: function (appswitcher, overapp) {
        this.appswitcher_displayed = !!appswitcher;
        this.backbutton_displayed = this.appswitcher_displayed && !!overapp;

        this.$menu_toggle.toggleClass('fa-chevron-left', this.appswitcher_displayed)
                         .toggleClass('fa-th', !this.appswitcher_displayed);
        if (this.appswitcher_displayed && !this.backbutton_displayed) {
            this.$menu_toggle.removeAttr('accesskey');
        } else {
            this.$menu_toggle.attr('accesskey', 'h');
        }
        this.$menu_toggle.toggleClass('hidden', this.appswitcher_displayed && !this.backbutton_displayed);
        this.$menu_brand_placeholder.toggleClass('hidden', this.appswitcher_displayed);
        this.$section_placeholder.toggleClass('hidden', this.appswitcher_displayed);
    },
    change_menu_section: function (primary_menu_id) {
        if (!this.$menu_sections[primary_menu_id]) {
            return; // unknown menu_id
        }

        if (this.current_primary_menu === primary_menu_id) {
            return; // already in that menu
        }

        if (this.current_primary_menu) {
            this.$menu_sections[this.current_primary_menu].detach();
        }

        // Get back the application name
        for (var i = 0; i < this.menu_data.children.length; i++) {
            if (this.menu_data.children[i].id === primary_menu_id) {
                this.$menu_brand_placeholder.text(this.menu_data.children[i].name);
                break;
            }
        }

        this.$menu_sections[primary_menu_id].appendTo(this.$section_placeholder);
        this.current_primary_menu = primary_menu_id;

        this._handle_extra_items();
    },
    _trigger_menu_clicked: function(menu_id, action_id) {
        this.trigger_up('menu_clicked', {
            id: menu_id,
            action_id: action_id,
            previous_menu_id: this.current_secondary_menu || this.current_primary_menu,
        });
    },
    _on_secondary_menu_click: function(menu_id, action_id) {
        var self = this;

        // It is still possible that we don't have an action_id (for example, menu toggler)
        if (action_id) {
            self._trigger_menu_clicked(menu_id, action_id);
            this.current_secondary_menu = menu_id;
        }
    },
    /**
     * Helpers used by web_client in order to restore the state from
     * an url (by restore, read re-synchronize menu and action manager)
     */
    action_id_to_primary_menu_id: function (action_id) {
        var primary_menu_id, found;
        for (var i = 0; i < this.menu_data.children.length && !primary_menu_id; i++) {
            found = this._action_id_in_subtree(this.menu_data.children[i], action_id);
            if (found) {
                primary_menu_id = this.menu_data.children[i].id;
            }
        }
        return primary_menu_id;
    },
    _action_id_in_subtree: function (root, action_id) {
        // action_id can be a string or an integer
        if (root.action && root.action.split(',')[1] === String(action_id)) {
            return true;
        }
        var found;
        for (var i = 0; i < root.children.length && !found; i++) {
            found = this._action_id_in_subtree(root.children[i], action_id);
        }
        return found;
    },
    menu_id_to_action_id: function (menu_id, root) {
        if (!root) {
            root = $.extend(true, {}, this.menu_data);
        }

        if (root.id === menu_id) {
            return root.action.split(',')[1] ;
        }
        for (var i = 0; i < root.children.length; i++) {
            var action_id = this.menu_id_to_action_id(menu_id, root.children[i]);
            if (action_id !== undefined) {
                return action_id;
            }
        }
        return undefined;
    },
    _handle_extra_items: function () {
        if (!this.$el.is(":visible")) return;

        if (this.$extraItemsToggle) {
            this.$extraItemsToggle.find("> ul > *").appendTo(this.$section_placeholder);
            this.$extraItemsToggle.remove();
        }
        if (config.device.size_class < config.device.SIZES.SM) {
            return;
        }

        var width = this.$el.width();
        var menuItemWidth = this.$section_placeholder.outerWidth(true);
        var othersWidth = this.$menu_toggle.outerWidth(true) + this.$menu_brand_placeholder.outerWidth(true) + this.systray_menu.$el.outerWidth(true);

        if (width < menuItemWidth + othersWidth) {
            var $items = this.$section_placeholder.children();
            var nbItems = $items.length;
            menuItemWidth += 46; // @odoo-navbar-height (width of the "+" button)
            do {
                nbItems--;
                menuItemWidth -= $items.eq(nbItems).outerWidth(true);
            } while (width < menuItemWidth + othersWidth);

            var $extraItems = $items.slice(nbItems).detach();
            this.$extraItemsToggle = $("<li/>", {"class": "o_extra_menu_items"});
            this.$extraItemsToggle.append($("<a/>", {href: "#", "class": "dropdown-toggle fa fa-plus", "data-toggle": "dropdown"}));
            this.$extraItemsToggle.append($("<ul/>", {"class": "dropdown-menu"}).append($extraItems));
            this.$extraItemsToggle.appendTo(this.$section_placeholder);
        }
    },

    // Handlers

    /**
     * Display burger menu in mobile.
     * @private
     * @param {MouseEvent} event
     */
    _onBurgerMenuToggleClick: function (ev) {
        ev.preventDefault();
        var self = this;

        var menus = _.filter(this.menu_data.children, {'id': self.current_primary_menu});
        menus = menus.length && !self.appswitcher_displayed ? menus[0].children : [];
        this.$('.o_mobile_menu_container').animate({"right":"0%"}, 300).removeClass('o_hidden');
        this.$(".o_mobile_menu_container").html($(QWeb.render("Menu.Mobile.UserMenu", {session: session,enable_menu:menus.length})));
        var user_menu = new UserMenuMobile(this);
        user_menu.appendTo(this.$('.o_mobile_menu_user_menu_items'));

        if (menus.length) {
            this.$(".o_mobile_menu_content").append($(QWeb.render('Menu.Mobile.Sections', {'menu_items': menus})));
            this.$(".o_user_menu_caret_icon").removeClass("dropup");

            this.$('.o_mobile_menu_user_menu').on('click', this._onUserMenuClick.bind(this));
            this.$(".o_burger_menu_section").on('click', this._onBurgerMenuSectionClick.bind(this));
            this.$(".o_burger_menu_root a[data-menu]").on("click", function (event) {
                self._onBurgerMenuActionClick(event);
            });
            this.$(".o_mobile_menu_content").on('click', function () {
                self.$('.o_burger_menu_root span.fa-chevron-down').toggleClass("fa-chevron-down fa-chevron-right");
            });
        } else {
            this.$(".o_mobile_menu_content").removeClass("o_mobile_menu_darken");
            this.$('.o_mobile_menu_user_menus').removeClass("o_hidden");
        }

        this.$('.o_mobile_menu_user_company').on('click', function (e){
            self._onMultiCompanyClick(e);
        });
    },

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onBurgerMenuCloseClick: function () {
        var self = this;
        this.$('.o_mobile_menu_container').animate({"right": "100%"}, 300, function () {
            self.$('.o_mobile_menu_container').addClass("o_hidden");
        });
    },

    /**
     * Toggle user's preferences option and main menu.
     * @private
     * @param {MouseEvent} event
     */
    _onUserMenuClick: function () {
        this.$(".o_mobile_menu_content").toggleClass("o_mobile_menu_darken");
        this.$(".o_user_menu_caret_icon").toggleClass("dropup");
        this.$('.o_mobile_menu_app_menus').toggleClass("o_hidden");
        this.$('.o_burger_menu_root span.fa-chevron-down').toggleClass("fa-chevron-down fa-chevron-right");
    },

    /**
     * On section menu toggle the N-Level sub menu.
     * @private
     * @param {MouseEvent} event
     */
    _onBurgerMenuSectionClick: function (e) {
        e.preventDefault();
        e.stopPropagation();
        var $target = $(e.currentTarget);
        var $opened = !$target.parents(".o_burger_menu_section.open").length ? this.$(".o_burger_menu_section.open").not(this) : $target.parent().find(".o_burger_menu_section.open").not(this);
        $opened.removeClass("open");
        $opened.find(".toggle_icon:first()").toggleClass("fa-chevron-down fa-chevron-right");
        $target.toggleClass("open");
        $target.find(".toggle_icon:first()").toggleClass("fa-chevron-down fa-chevron-right");
    },

    /**
     * On menu click redirect to particular action.
     * @private
     * @param {MouseEvent} event
     */
    _onBurgerMenuActionClick: function (ev) {
        ev.preventDefault();
        this._on_secondary_menu_click($(ev.currentTarget).data('menu'), $(ev.currentTarget).data('action-id'));
        this._onBurgerMenuCloseClick();
    },

    /**
     * Switch company.
     * @private
     * @param {MouseEvent} event
     */
    _onMultiCompanyClick: function (ev) {
        ev.preventDefault();
        var companyID = $(ev.currentTarget).data('id');
        this._rpc({
            model: 'res.users',
            method: 'write',
            args: [[session.uid], {'company_id': companyID}],
        }).then(function () {
            window.location.reload();
        });
    },

    /**
     * When clicking on the main menu title, we want to open the first action of
     * the current application
     *
     * @private
     */
    _onMainMenuClick: function () {
        var actionID = this.menu_id_to_action_id(this.current_primary_menu);
        this._trigger_menu_clicked(this.current_primary_menu, actionID);
    }
});

return Menu;
});
