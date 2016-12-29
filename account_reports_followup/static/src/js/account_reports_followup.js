odoo.define('account_reports_followup.account_report_followup', function (require) {
'use strict';

var Model = require('web.Model');
var account_report_followup = require('account_reports.account_report_followup');

account_report_followup.include({
    events: _.defaults({
        'click .followup-action': 'do_manual_action',
    }, account_report_followup.prototype.events),

    do_manual_action: function(e) {
        var self = this;
        var partner_id = $(e.target).data('partner');
        this.report_options['partner_id'] = partner_id;
        return new Model(this.report_model).call('do_manual_action', [this.report_options]).then(function (result) { // send the email server side
            self.display_done(e);
        });
    },
});
});
