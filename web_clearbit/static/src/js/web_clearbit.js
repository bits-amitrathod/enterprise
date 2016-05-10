odoo.define('web_clearbit.autocomplete', function (require) {
'use strict';

var core = require('web.core');
var form_widgets = require('web.form_widgets');

var QWeb = core.qweb;

var FieldClearbit = form_widgets.FieldChar.extend({
    events: _.extend({}, form_widgets.FieldChar.prototype.events, {
        'keydown': 'keydown_input',
        'keyup': 'keyup_input',
        'blur': 'remove_dropdown'
    }),
    init: function (field_manager, node) {
        this._super(field_manager, node);
        this.options = {
            min_length: 0,
            typing_speed: 400,
        };
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
        if(this.field_manager.get_field_value('is_company')) {
            switch(event.which) {
                case $.ui.keyCode.ESCAPE:
                    this.remove_dropdown();
                    break;
                case $.ui.keyCode.ENTER:
                    this.on_select_dropdown();
                    break;
                default:
                    this.input_value = this.$el.val().trim();
                    if(this.dropdown_query != this.input_value) {
                        this.show_dropdown();
                    }
            }
        }
    },
    show_dropdown: function () {
        var self = this;
        clearTimeout(this.fetch_timer);
        if(this.input_value.length > this.options.min_length) {
            this.fetch_timer = setTimeout(function () {
                self.get_clearbit_values();
            }, this.options.typing_speed);
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
        var $active = this.$dropdown.find('.o_clearbit_suggestion.active');
        if($active.length == 1) {
            var result = this.suggestions[$active.data('index')];
            if(result.logo) {
                this.get_image_base64(result.logo, function (result) {
                    if(result === '404'){
                        self.field_manager.set_values({'image': false});
                    }else{
                        var img_base64 = result.replace(/^data:image[^;]*;base64,?/, '');
                        // If image not available on given url it simply return "data:"
                        self.field_manager.set_values({'image': img_base64 == "data:" ? false : img_base64});
                    }
                });
            } else {
                this.field_manager.set_values({'image': false});
            }
            this.field_manager.set_values({'name': result.name, 'website': result.domain});
            this.remove_dropdown();
        }
    },
    get_image_base64: function (url, callback) {
        var xhr = new XMLHttpRequest();
        xhr.responseType = 'blob';
        xhr.onload = function () {
            var reader  = new FileReader();
            reader.onloadend = function () {
                callback(reader.result);
            };
            reader.readAsDataURL(xhr.response);
        };
        xhr.open('GET', url);
        xhr.onerror = function(){
            callback('404');
        };
        xhr.send();
    }
});

core.form_widget_registry.add('field_clearbit', FieldClearbit);

});
