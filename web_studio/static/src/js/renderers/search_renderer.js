odoo.define('web_studio.SearchRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var core = require('web.core');
var session = require('web.session');

var qweb = core.qweb;


var SearchRenderer = AbstractRenderer.extend({
    className: "o_search_view",
    _render: function() {
        var self = this;
        this.$el.empty();
        this.$el.html(qweb.render('web_studio.searchRenderer', this.widget));
        this.first_field = undefined;
        this.first_filter = undefined;
        this.first_group_by = undefined;
        _.each(this.arch.children, function (node) {
            if (node.tag === "field"){
                if (!self.first_field){
                    self.first_field = node;
                }
                self._render_field(node);
            } else if (node.tag === "filter") {
                if (!self.first_filter){
                    self.first_filter = node;
                }
                self._render_filter(node);
            } else if (node.tag === "separator") {
                if (!self.first_filter){
                    self.first_filter = node;
                }
                self._render_separator(node);
            } else if (node.tag === "group") {
                if (!self.first_group_by){
                    self.first_group_by = node;
                }
                self._process_group_by(node);
            }
        });
        return this._super.apply(this, arguments);
    },
    _render_field: function(node) {
        var $tbody = this.$('.o_web_studio_search_autocompletion_fields tbody');
        var field_string = this.fields[node.attrs.name].string;
        var display_string = node.attrs.string || field_string;
        if (session.debug) {
            display_string += ' (' + node.attrs.name +')';
        }
        var $new_row = $('<tr>').append(
            $('<td>').append(
            $('<span>').text(display_string)
        ));
        $tbody.append($new_row);
        return $new_row;
    },
    _render_filter: function(node) {
        var $tbody = this.$('.o_web_studio_search_filters tbody');
        var display_string = node.attrs.string || node.attrs.help;
        var $new_row = $('<tr>').append(
            $('<td>').append(
            $('<span>').text(display_string)
        ));
        $tbody.append($new_row);
        return $new_row;
    },
    _render_separator: function(node) {
        var $tbody = this.$('.o_web_studio_search_filters tbody');
        var $new_row = $('<tr class="o_web_studio_separator">').html('<td><hr/></td>');

        $tbody.append($new_row);
        return $new_row;
    },
    _render_group_by: function(node) {
        var $tbody = this.$('.o_web_studio_search_group_by tbody');
        // the domain is define like this:
        // context="{'group_by': 'field'}"
        // we use a regex to get the field string
        var display_string = node.attrs.string;
        var field_name = node.attrs.context.match(":.?'(.*)'")[1];
        if (session.debug) {
            display_string += ' (' + field_name +')';
        }
        var $new_row = $('<tr>').append(
            $('<td>').append(
            $('<span>').text(display_string)
        ));
        $tbody.append($new_row);
        return $new_row;
    },
    _process_group_by: function(groups) {
        var self = this;
        _.each(groups.children, function (node) {
            if (node.tag === "filter"){
                self._render_group_by(node);
            }
        });
    },
});

return SearchRenderer;

});
