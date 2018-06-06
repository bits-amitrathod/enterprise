odoo.define('mail_enterprise.form_renderer', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var pyeval = require('web.pyeval');
var FormRenderer = require('web.FormRenderer');

var QWeb = core.qweb;

/**
 * Display attachment preview on side of form view for large screen devices.
 *
 * To use this simply add div with class o_attachment_preview in format
 *     <div class="o_attachment_preview"/>
 *
 * Some options can be passed to change its behavior:
 *     types: ['image', 'pdf']
 *     order: 'asc' or 'desc'
 *
 * For example, if you want to display only pdf type attachment and the latest
 * one then use:
 *     <div class="o_attachment_preview" options="{'types': ['pdf'], 'order': 'desc'}"/>
**/

FormRenderer.include({
    custom_events: _.extend({}, FormRenderer.prototype.custom_events, {
        preview_attachment: '_onAttachmentPreview'
    }),

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);

        this.$attachmentPreview = undefined;
        this.attachmentPreviewID = undefined;
        this.attachmentPreviewResID = undefined;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Interchange the position of the chatter and the attachment preview.
     *
     * @private
     * @param {boolean} enablePreview
     */
    _interchangeChatter: function (enablePreview) {
        if (config.device.size_class < config.device.SIZES.XL) {
            return;
        }
        if (!this.$attachmentPreview) {
            return;
        }
        var $sheet = this.$('.o_form_sheet_bg');

        if (enablePreview) {
            this.chatter.$el.appendTo($sheet);
            this.$attachmentPreview.insertAfter($sheet);
        } else {
            this.chatter.$el.insertAfter($sheet);
            this.$attachmentPreview.appendTo($sheet);
        }
    },
    /**
     * Overrides the function that renders the nodes to return the preview's $el
     * for the `o_attachment_preview` div node.
     *
     * @private
     * @override
     */
    _renderNode: function (node) {
        if (node.tag === 'div' && node.attrs.class === 'o_attachment_preview') {
            this.attachmentPreviewID = undefined;
            this.$attachmentPreview = $('<div>', {class: 'o_attachment_preview'});
            this._handleAttributes(this.$attachmentPreview, node);
            this._registerModifiers(node, this.state, this.$attachmentPreview);
            if (node.attrs.options) {
                this.$attachmentPreview.data(pyeval.py_eval(node.attrs.options));
            }
            if (this.attachmentPreviewWidth) {
                this.$attachmentPreview.css('width', this.attachmentPreviewWidth);
            }
            return this.$attachmentPreview;
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides the function to interchange the chatter and the preview once
     * the chatter is in the dom.
     *
     * @private
     * @override
     */
    _renderView: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            // for cached messages, `preview_attachment` will be triggered
            // before the view rendering where the chatter is replaced ; in this
            // case, we need to interchange its position if needed
            var enablePreview = self.attachmentPreviewResID &&
                self.attachmentPreviewResID === self.state.res_id &&
                self.$attachmentPreview &&
                !self.$attachmentPreview.hasClass('o_invisible_modifier');
            self._interchangeChatter(enablePreview);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Triggered from the mail chatter, send attachments data for preview
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onAttachmentPreview: function (ev) {
        if (config.device.size_class < config.device.SIZES.XL) {
            return;
        }
        if (!this.$attachmentPreview) {
            return;
        }
        var self = this;
        var options = _.defaults(this.$attachmentPreview.data(), {
            types: ['pdf', 'image'],
            order: 'asc'
        });
        var attachments = ev.data.attachments.slice();  // clone array
        attachments = _.filter(attachments, function (attachment) {
            var match = attachment.mimetype.match("(image|pdf)");
            attachment.type = match ? match[0] : false;
            return attachment.type;
        });
        if (options.order === 'desc') {
            attachments.reverse();
        }
        var attachment = _.find(attachments, function (attachment) {
            return options.preview_priority_type == attachment.type;
        });
         if (!attachment) {
            attachment = _.find(attachments, function (attachment) {
                return _.contains(options.types, attachment.type);
            });
        }
        if (attachment && attachment.id !== this.attachmentPreviewID) {
            this.attachmentPreviewID = attachment.id;
            this.attachmentPreviewResID = this.state.res_id;
            // need to remove and append because resizer adds its element
            this.$attachmentPreview.find('.o_attachment_preview_container').remove();
            this.$attachmentPreview.append(QWeb.render('AttachmentPreview', {
                attachment: attachment,
            }));
            this.$attachmentPreview.resizable({
                handles: 'w',
                minWidth: 400,
                maxWidth: 900,
                resize: function (event, ui) {
                    self.attachmentPreviewWidth = ui.size.width;
                },
            });
            this._interchangeChatter(!this.$attachmentPreview.hasClass('o_invisible_modifier'));
        }
    },

});

});
