odoo.define('documents.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('documents_tour', {
    test: true,
    url: "/web",
}, [{
    trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
    content: _t("Here is the place to manage your documents."),
    position: 'bottom',
}]);

});
