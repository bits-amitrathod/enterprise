odoo.define('web_clearbit.autocomplete', function (require) {
'use strict';

var basic_fields = require('web.basic_fields');
var core = require('web.core');
var field_registry = require('web.field_registry');

var QWeb = core.qweb;

var FieldChar = basic_fields.FieldChar;

var FieldClearbit = FieldChar.extend({
    events: _.extend({}, FieldChar.prototype.events, {
        'keydown': 'keydown_input',
        'keyup': 'keyup_input',
        'blur': 'remove_dropdown'
    }),
    init: function () {
        this._super.apply(this, arguments);
        this.fetch_timer = null;
        this.dropdown_query = false;
    },
    // Trigger the navigation in the dropdown when "down" or "up" keys are pressed
    // Triggered by keydown to execute the navigation multiple times when the user keeps the "down" or "up" pressed
    keydown_input: function (event) {
        switch(event.which) {
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
                if(this.dropdown_query) {
                    event.preventDefault();
                    this.navigation_dropdown(event.which);
                }
        }
    },
    keyup_input: function (event) {
        if(this.recordData.is_company) { // This widget only works for the res.partner model
            switch(event.which) {
                case $.ui.keyCode.ESCAPE:
                    this.remove_dropdown();
                    break;
                case $.ui.keyCode.ENTER:
                    this.on_select_dropdown();
                    break;
                default:
                    this.input_value = this.$el.val().trim();
                    if(this.dropdown_query !== this.input_value) {
                        this.show_dropdown();
                    }
            }
        }
    },
    show_dropdown: function () {
        clearTimeout(this.fetch_timer);
        if(this.input_value.length > 0) {
            this.fetch_timer = setTimeout(this.get_clearbit_values.bind(this), 400);
        } else {
            this.remove_dropdown();
        }
    },
    get_clearbit_values: function () {
        var self = this;
        var clearbit_url = _.str.sprintf('https://autocomplete.clearbit.com/v1/companies/suggest?query=%s', this.input_value);
        $.ajax({
            url: clearbit_url,
            type: 'GET',
            dataType: 'json',
            success: function (suggestions) {
                self.suggestions = suggestions;
                self.build_dropdown();
            }
        });
    },
    build_dropdown: function () {
        this.remove_dropdown();
        if(this.suggestions.length > 0){
            this.$dropdown = $(QWeb.render('web_clearbit.dropdown', {suggestions: this.suggestions}));
            this.$dropdown.insertAfter(this.$el);
            this.$dropdown.find('.o_clearbit_suggestion')
                .on('mouseover', this.on_hover_dropdown)
                .on('mousedown', this.on_select_dropdown);
            this.dropdown_query = this.input_value;
        }
    },
    remove_dropdown: function () {
        if(this.$dropdown) {
            this.$dropdown.remove();
        }
        this.dropdown_query = false;
    },
    navigation_dropdown: function (keycode) {
        var $active = this.$dropdown.find('.o_clearbit_suggestion.active');
        var $to = keycode === $.ui.keyCode.DOWN ? $active.next('.o_clearbit_suggestion') : $active.prev('.o_clearbit_suggestion');
        if ($to.length) {
            $active.removeClass('active');
            $to.addClass('active');
        }
    },
    on_hover_dropdown: function (event) {
        this.$dropdown.find('.o_clearbit_suggestion.active').removeClass('active');
        this.$dropdown.find(event.currentTarget).addClass('active');
    },
    on_select_dropdown: function () {
        var self = this;
        if (!this.$dropdown) {
            return;
        }
        var $active = this.$dropdown.find('.o_clearbit_suggestion.active');
        if($active.length === 1) {
            var result = this.suggestions[$active.data('index')];
            var def;
            if(result.logo) {
                def = this.get_image_base64(result.logo);
            }
            $.when(def).always(function (image_base64) {
                var value = false;
                if(image_base64){
                    value = image_base64.replace(/^data:image[^;]*;base64,?/, '');
                    // image_base64 equals "data:" if image not available on given url
                }
                self.trigger_up('field_changed', {
                    dataPointID: self.dataPointID,
                    changes: {
                        name: result.name,
                        website: result.domain,
                        image: value,
                    },
                });
            });
            this.$el.val(this.format_value(result.name)); // update the input's value directly
            this.remove_dropdown();
        }
    },
    get_image_base64: function (url) {
        var def = $.Deferred();
        var xhr = new XMLHttpRequest();
        xhr.responseType = 'blob';
        xhr.onload = function () {
            var reader  = new FileReader();
            reader.onloadend = function () {
                def.resolve(reader.result);
            };
            reader.readAsDataURL(xhr.response);
        };
        xhr.open('GET', url);
        xhr.onerror = def.reject.bind(def);
        xhr.send();
        return def;
    }
});

field_registry.add('field_clearbit', FieldClearbit);

});
