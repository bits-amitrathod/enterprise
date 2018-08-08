odoo.define('web_one2many_selectable.form_widgets', function (require) {
"use strict";

/**
 * This file defines a client action that opens in a dialog (target='new') and
 * allows the user to change his password.
 */
var core = require('web.core');
var AbstractField = require('web.AbstractField');
var Widget = require('web.Widget');
var web_client = require('web.web_client');
var fieldRegistry = require('web.field_registry');
var FieldOne2Many=fieldRegistry.get("one2many");
var _t = core._t;
var One2ManySelectable = FieldOne2Many.extend({
    template: "One2ManySelectable",
/**
     * @fixme: weird interaction with the parent for the $buttons handling
     *
     * @override
     * @returns {Deferred}
     */
    /* init: function() {
        var result = this._super.apply(this, arguments);
        console.log("inside init");
        //console.log(this);
        //this.renderer.hasSelectors=true;
       // console.log(this.renderer.hasSelectors)

         //rendererParams
         //this.__getterSetterInternalMap({renderer:{hasSelectors:true}})
        //console.log(this.__getterSetterInternalMap(renderer:{hasSelectors:true}));
       // console.log(this.);
        return result;
    },*/
    events: {
        "click .cf_button_confirm": "action_selected_lines",
    },
    start: function () {
        //console.log("inside start");
        this._super.apply(this, arguments);
        var result=this._super.apply(this, arguments);
    	return result;
    },

   _render: function () {
          this._super.apply(this, arguments);
          if(this.renderer.hasSelectors){
          }else{
            this.renderer.hasSelectors=true;
          }
   },
    action_selected_lines: function()
	{
			var self=this;
			//console.log(this.value);
			var selected_ids = this.renderer.selection;
			if (selected_ids.length === 0)
			{
				this.do_warn(_t("You must choose at least one record."));
				return false;
			}

/* you can use the python function to get the IDS
			      @api.multi
				def bulk_verify(self):
        				for record in self:
            				print record
			*/
			return this._rpc({
                model:this.model,
                method: 'bulk_verify',
                args: [selected_ids, {context:this.context,value:this.value}],
                });
		},
});

fieldRegistry.add("one2many_selectable", One2ManySelectable);
return One2ManySelectable;

});
//args: [selected_ids, {context:this.context}],