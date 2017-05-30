odoo.define('voip.Activity', function (require) {
"use strict";

var MailActivity = require('mail.Activity');

var Activity = MailActivity.include({
    events: _.extend({}, MailActivity.prototype.events, {
        'click .o_activity_voip_call': '_onVoipCall',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param  {Event} event
     */
    _onVoipCall: function (event) {
        event.preventDefault();
        this.trigger_up('voip_activity_call', {
            number: event.currentTarget.text.trim(),
            activityId: $(event.currentTarget).data('activity-id'),
        });
    }
});

return Activity;

});