// FIXME: all this should be done directly in community

// odoo.define('web_enterprise.FormView', function (require) {
// "use strict";

// var config = require('web.config');
// var FormRenderingEngineMobile = require('web_enterprise.FormRenderingEngineMobile');
// var FormView = require('web.FormView');

// FormView.include({
//     defaults: _.extend({}, FormView.prototype.defaults, {
//         disable_autofocus: config.device.touch,
//     }),
//     init: function () {
//         this._super.apply(this, arguments);
//         if (config.device.size_class <= config.device.SIZES.XS) {
//             this.rendering_engine = new FormRenderingEngineMobile(this);
//         }
//     },
// });

// });

// odoo.define('web_enterprise.FormRenderingEngineMobile', function (require) {
// "use strict";

// var FormRenderingEngine = require('web.FormRenderingEngine');

// return FormRenderingEngine.extend({
//     fill_statusbar_buttons: function ($statusbar_buttons, $buttons) {
//         if(!$buttons.length) {
//             return;
//         }
//         var $statusbar_buttons_dropdown = this.render_element('FormRenderingStatusBar_DropDown', {});
//         $buttons.each(function(i, el) {
//             $statusbar_buttons_dropdown.find('.dropdown-menu').append($('<li/>').append(el));
//         });
//         $statusbar_buttons.append($statusbar_buttons_dropdown);
//     },
// });

// });
