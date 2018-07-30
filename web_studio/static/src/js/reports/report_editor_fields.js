odoo.define('web_studio.report_fields', function (require) {
"use strict";

var fieldRegistry = require('web.field_registry');
var relationalFields = require('web.relational_fields');

/**
 * This widget is used only for rendering by the report editor (the widget options)
 *
 */


var FieldMany2ManySelection = relationalFields.FieldMany2ManyTags.extend({
    custom_events: _.extend({}, relationalFields.FieldMany2ManyTags.prototype.custom_events, {
        call_service: '_onCallService',
    }),
    init: function (parent, name, record, options) {
        this._super.apply(this, arguments);

        options.quick_create = false;
        options.can_create = false;

        var selection = options.attrs.selection;
        if (typeof selection[0] === 'string') {
            selection = _.map(selection, function (s) { return [s, s];});
        }
        this.selection = _.map(selection, function (s) {
            return {id: s[0], res_id: s[0], data: {id: s[0], display_name: s[1]}};
        });
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {Moment|false} value
     * @returns {boolean}
     */
    _isSameValue: function (value) {
        if (value === false) {
            return this.value === false;
        }
        return value.length === this.value.res_ids.length &&
            _.difference(value, this.value.res_ids).length === 0;
    },
    /**
     *
     * @overwrite
     */
    _render: function () {
        var res_ids = this.value.res_ids;
        this.value.data = _.filter(this.selection, function (s) {
            return res_ids.indexOf(s.id) !== -1;
        });
        this._super.apply(this, arguments);
    },
    /**
     *
     * @overwrite
     */
    _setValue: function (value, options) {
        var def = $.Deferred();
        var selection = this.value.res_ids;

        switch (value.operation) {
            case "ADD_M2M":
                selection = selection.concat([value.ids.id]);
                break;
            case "FORGET":
                selection = _.difference(selection, value.ids);
                break;
            default: throw Error('Not implemented');
        }

        if (!(options && options.forceChange) && this._isSameValue(selection)) {
            return $.when();
        }

        this.value.res_ids = selection;
        this._render();

        this.trigger_up('field_changed', {
            dataPointID: this.dataPointID,
            changes: _.object([this.name], [{
                operation: 'REPLACE_WITH',
                ids: selection,
            }]),
            viewType: this.viewType,
            doNotSetDirty: options && options.doNotSetDirty,
            notifyChange: !options || options.notifyChange !== false,
            onSuccess: def.resolve.bind(def),
            onFailure: def.reject.bind(def),
        });
        return def;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * Intercept search_read to use field options
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCallService: function (e) {
        e.stopPropagation();
        var kwargs = e.data.args[1].kwargs;
        var name = kwargs.name;
        var notInIds = kwargs.args[0][2];
        var records = _.filter(_.pluck(this.selection, 'data'), function (r) {
            return r.display_name.indexOf(name) !== -1 && notInIds.indexOf(r.id) === -1;
        });
        var selection = _.map(records.slice(0, kwargs.limit), function (r) {return [r.id, r.display_name];});
        e.data.callback($.Deferred().resolve(selection));
    },
});

fieldRegistry.add('many2many_select', FieldMany2ManySelection);

return {
    FieldMany2ManySelection: FieldMany2ManySelection,
};

});

