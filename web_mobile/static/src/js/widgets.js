odoo.define('web_mobile.widgets', function (require) {
"use strict";

var mobile = require('web_mobile.rpc');
var AbstractField = require('web.AbstractField');
var web_datepicker = require('web.datepicker');
var field_registry = require('web.field_registry');
var session = require('web.Session');
var relational_fields = require('web.relational_fields');
var notification_manager = require('web.notification').NotificationManager;
var UserMenu = require('web.UserMenu');
var crashManager = require('web.CrashManager');

/*
    Override odoo date-picker(bootstrap date-picker) to display mobile native date picker
    Because of it is better to show native mobile date-picker to improve usability of Application
    (Due to Mobile users are used to native date picker)
*/
web_datepicker.DateWidget.include({
    start: function(){
        this._super.apply(this, arguments);
        if(mobile.methods.requestDateTimePicker){
            //  super will initiate bootstrap date-picker object which is not required in mobile application.
            if(this.picker){
                this.picker.destroy();
            }
            this.set_readonly(true);
            this.setup_mobile_picker();
        }
    },
    setup_mobile_picker: function(){
        var self = this;
        this.$el.on('click', function() {
            mobile.methods.requestDateTimePicker({
                'value': self.get_value(),
                'type': self.type_of_date
            }).then(function(response) {
                self.set_value(response.data);
                self.commit_value();
            });
        });
    }
});

/*
    Android webview not supporting post download and odoo is using post method to download
    so here override get_file of session and passed all data to native mobile downloader
    ISSUE: https://code.google.com/p/android/issues/detail?id=1780
*/

session.include({
    get_file: function (options) {
        if(mobile.methods.downloadFile){
            mobile.methods.downloadFile(options);
            if (options.complete) { options.complete(); }
        }else{
            this._super.apply(this, arguments);
        }
    }
});

/*
    Android webview not supporting post download and odoo is using post method to download
    so here override get_file of session and passed all data to native mobile downloader
    ISSUE: https://code.google.com/p/android/issues/detail?id=1780
*/

relational_fields.FieldMany2One.include({
    // TODO
    // render_editable: function(){
    //     var self = this;
    //     this._super.apply(this, arguments);
    //     if(mobile.methods.many2oneDialog){
    //         this.$el.find('input').prop('disabled', true);
    //         $(this.$el).on('click', self.on_mobile_click);
    //     }
    // },
    // on_mobile_click:function(e){
    //     if(!$(e.target).hasClass('o_external_button')){
    //         this.do_invoke_mobile_dialog('');
    //     };
    // },
    // do_invoke_mobile_dialog: function(term){
    //     var self = this;
    //     this.get_search_result(term).done(function(result) {
    //         self._callback_actions = {}

    //         _.each(result, function(r, i){
    //             if(!r.hasOwnProperty('id')){
    //                 self._callback_actions[i] = r.action;
    //                 result[i]['action_id'] = i;
    //             }
    //         })
    //         mobile.methods.many2oneDialog({'records': result, 'label': self.string})
    //             .then(function(response){
    //                 if(response.data.action == 'search'){
    //                     self.do_invoke_mobile_dialog(response.data.term);
    //                 }
    //                 if(response.data.action == 'select'){
    //                     self.reinit_value(response.data.value.id);
    //                 }
    //                 if(response.data.action == 'action'){
    //                     self._callback_actions[response.data.value.action_id]();
    //                 }
    //             });
    //     });
    // }
});


notification_manager.include({
    display:function(notification){
        if(mobile.methods.vibrate){
            mobile.methods.vibrate({'duration': 100})
        }
        return this._super.apply(this, arguments);
    }
})

// Hide the logout link in mobile
UserMenu.include({
    start:function(){
        if(mobile.methods.switchAccount){
            this.$('a[data-menu="logout"]').addClass('hidden');
            this.$('a[data-menu="account"]').addClass('hidden');
            this.$('a[data-menu="switch_account"]').removeClass('hidden');
        }
        return this._super();
    },
    on_menu_switch_account:function(){
        mobile.methods.switchAccount();
    }
});

crashManager.include({
    rpc_error:function(error){
        if(mobile.methods.crashManager){
            mobile.methods.crashManager(error);
        }
        return this._super.apply(this, arguments);
    }
});

// var ContactSync = common.FormWidget.extend({
//     template: 'ContactSync',
//     events: {
//         'click': 'on_click',
//     },
//     init: function(){
//         this.is_mobile = mobile.methods.addContact;
//         return this._super.apply(this, arguments);
//     },
//     on_click: function(){
//         this.field_manager.dataset.read_index(['name', 'image', 'parent_id', 'phone', 'mobile', 'fax', 'email', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id','website','function', 'title'], {}).then(function(r) {
//             mobile.methods.addContact(r);
//         });
//     },
// });

field_registry.add('contactsync', AbstractField); // TODO

});