odoo.define('website_studio.SubMenu', function (require) {
"use strict";

var SubMenu = require('web_studio.SubMenu');

var WebsiteSubMenu = SubMenu.include({
    template: 'website_studio.SubMenu',

    /**
     * @override
     *
     * Add the event when clicking on the website form menu added in the submenu
     */
    on_menu_click: function (ev) {
        this._super.apply(this, arguments);

        var $menu = $(ev.currentTarget);
        var title = $menu.text();
        if ($menu.data('name') === 'website'){
            this.replace_action('action_web_studio_form', title, {
                action: this.action,
                clear_breadcrumbs: true,
                disable_edition: true,
            });
        }
    },
});

return WebsiteSubMenu;

});
