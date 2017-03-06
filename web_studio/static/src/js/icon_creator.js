odoo.define('web_studio.IconCreator', function (require) {
"use strict";

var core = require('web.core');
var session = require('web.session');
var Widget = require('web.Widget');

var utils = require('web_studio.utils');

var QWeb = core.qweb;

return Widget.extend({
    template: 'web_studio.IconCreator',
    events: {
        'click .o_web_studio_selector': 'on_selector',
        'click .js_upload': 'on_upload_button',
        'click .js_discard_upload': 'on_upload_discarded',
    },

    init: function() {
        this.COLORS = utils.COLORS;
        this.BG_COLORS = utils.BG_COLORS;
        this.ICONS = utils.ICONS;

        this.color = this.COLORS[4];
        this.background_color = this.BG_COLORS[5];
        this.icon_class = this.ICONS[0];

        this.PALETTE_TEMPLATES = {
            'color':            'web_studio.IconCreator.IconColorPalette',
            'background_color': 'web_studio.IconCreator.BgPalette',
            'icon':             'web_studio.IconCreator.IconPalette',
        };

        // Upload related stuff
        this.uploaded = false;
        this.uploaded_attachment_id = false;
        this.widget = "image";
        this.user_id = session.uid;
        this.fileupload_id = _.uniqueId('o_fileupload');
        $(window).on(this.fileupload_id, this.on_upload_done.bind(this));

        this.mode = 'edit';
        this._super.apply(this, arguments);
    },
    destroy: function() {
        $(window).off(this.fileupload_id);
        return this._super.apply(this, arguments);
    },
    /* Returns the value of the icon

     * It can either be:
     *  - the ir.attachment id of the uploaded image
     *  - if the icon has been created, an array containing: [icon_class, color, background_color]
     */
    get_value: function() {
        if (this.uploaded) {
            return this.uploaded_attachment_id;
        } else {
            return [this.icon_class, this.color, this.background_color];
        }
    },
    start: function() {
        this.update(true);
        return this._super.apply(this, arguments);
    },
    update: function(replace_icon) {
        var self = this;
        this.$('.o_app_icon').css('background-color', this.background_color)
                             .find('i').css('color', this.color);

        if (replace_icon) {
            this.$('.o_app_icon i').fadeOut(50, function() {
                $(this).attr('class', self.icon_class).fadeIn(800);
            });
        }

        this.$('.o_web_studio_selector[data-type="icon"] i').attr('class', self.icon_class);
        this.$('.o_web_studio_selector[data-type="background_color"]').css('background-color', this.background_color);
        this.$('.o_web_studio_selector[data-type="color"]').css('background-color', this.color);
    },
    on_selector: function(ev) {
        var self = this;
        var selector_type = $(ev.currentTarget).data('type');

        if (!selector_type) { return; }
        if (this.$palette) { this.$palette.remove(); }

        this.$palette = $(QWeb.render(this.PALETTE_TEMPLATES[selector_type], {widget: this}));
        $(ev.currentTarget).addClass('active').find('.o_web_studio_selector_pointer').before(this.$palette);
        this.$palette.on('mouseleave', function() {
            $(this).remove();
            $(ev.currentTarget).removeClass('active');
        });
        this.$palette.find('.o_web_studio_selector').click(function(ev) {
            if (selector_type === 'background_color') {
                self.background_color = $(ev.currentTarget).data('color');
                self.update();
            } else if (selector_type === 'color') {
                self.color = $(ev.currentTarget).data('color');
                self.update();
            } else {
                self.icon_class = $(ev.currentTarget).children('i').attr('class');
                self.update(true);
            }
        });
    },
    on_upload_button: function(event) {
        event.preventDefault();

        var self = this;
        this.$('input.o_form_input_file').on('change', function() {
            self.$('form.o_form_binary_form').submit();
        });
        this.$('input.o_form_input_file').click();

    },
    on_upload_done: function(event, result) {
        event.preventDefault();

        this.uploaded = true;
        this.uploaded_attachment_id = result.id;

        var self = this;
        this._rpc('ir.attachment', 'read')
            .args([[this.uploaded_attachment_id], ['datas']])
            .exec()
            .then(function (res) {
                self.uploaded_image = ('data:image/png;base64,' + res[0].datas).replace(/\s/g, '');
                self.renderElement();
            });
    },
    on_upload_discarded: function(event) {
        event.preventDefault();

        this.uploaded = false;
        this.uploaded_attachment_id = false;
        this.renderElement();
        this.update(true);
    },
    enable_edit: function() {
        this.mode = 'edit';
        this.renderElement();
    },
    disable_edit: function() {
        this.mode = 'readonly';
        this.renderElement();
    },
});

});
