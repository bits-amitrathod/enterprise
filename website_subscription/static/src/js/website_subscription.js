odoo.define('website_subscription.website_subscription', function (require) {
    'use strict';

    require('web.dom_ready');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    if(!$('.oe_website_contract').length) {
        return $.Deferred().reject("DOM doesn't contain '.js_surveyresult'");
    }

    $('.contract-submit').off('click').on('click', function () {
        $(this).attr('disabled', true);
        $(this).prepend('<i class="fa fa-refresh fa-spin"></i> ');
        $(this).closest('form').submit();
    });

    var $new_payment_method = $('#new_payment_method');

    // When creating new pay method: create by json-rpc then continue with the new id in the form
    $new_payment_method.on('click', 'button[type="submit"]', function(ev) {
        var self = this;
        ev.preventDefault();
        ev.stopPropagation();
        $(this).attr('disabled', true);
        $(this).prepend('<i class="fa fa-refresh fa-spin"></i>');

        var $form = $(ev.currentTarget).parents('form');
        var action = $form.attr('action');
        var data = getFormData($form);
        var $main_form = $('#payment_tokens_list');

        ajax.jsonRpc(action, 'call', data).then(function(data){
          $main_form.prepend('<input name="pm_id" value="' + data + '" type="radio" checked="1" class="hidden"/>');
          $main_form.submit();
        }).fail(function(message, data){
          $(self).attr('disabled', false);
          $(self).find('i').remove();
          Dialog.alert(null, core._t("<p>We are not able to add your payment method at the moment.<br/> Please try again later or contact us.</p>") + (core.debug ? data.data.message : ''), {
            title: core._t('Error'),
          });
        });
});

    function getFormData($form){
        var unindexed_array = $form.serializeArray();
        var indexed_array = {};

        $.map(unindexed_array, function(n, i){
            indexed_array[n['name']] = n['value'];
        });

        return indexed_array;
    }
});
