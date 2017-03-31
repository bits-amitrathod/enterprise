odoo.define('sale_subscription.tour', function(require) {
"use_strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('sale_subscription_tour', {
	url: "/web",
}, [tour.STEPS.MENU_MORE, {
	trigger: '.o_app[data-menu-xmlid="sale_subscription.menu_sale_subscription_root"], .oe_menu_toggler[data-menu-xmlid="sale_subscription.menu_sale_subscription_root"]',
	content: _t('Want recurring billing via subscription management ? Get started by clicking here'),
	position: 'bottom',
}]);

});
