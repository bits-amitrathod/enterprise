odoo.define('mail_enterprise.AttachmentViewer', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var AttachmentViewer = Widget.extend({
    className: 'o_attachment_preview_container',
    events: {
        'click .arrow.o_move_next': '_onClickNext',
        'click .arrow.o_move_previous': '_onClickPrevious',
    },
    /**
     * The AttachmentViewer takes an array of objects describing attachments in
     * argument and first attachment of the array is display first.
     *
     * @constructor
     * @override
     * @param {Widget} parent
     * @param {Array<Object>} attachments list of attachments
     */
    init: function (parent, attachments) {
        this._super.apply(this, arguments);
        this.attachments = attachments;
        this.activeAttachment = attachments[0];
    },
    /**
     * Render attachment.
     *
     * @override
     */
    start: function () {
        this._renderAttachment();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Update attachments list and activeAttachment.
     *
     * @param {Array<Object>} attachments list of attachments
     * @param {string} order
     */
    updateContents: function (attachments, order) {
        this.attachments = attachments;
        // Display last uploaded attachment so a user can be notified that
        // attachments list is changed.
        this.activeAttachment = order === 'desc' ? attachments[0] : attachments[attachments.length - 1];
        this._renderAttachment();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Render template
     *
     * @private
     */
    _renderAttachment: function () {
        this.$el.empty();
        this.$el.append(QWeb.render('mail_enterprise.AttachmentPreview', {widget: this}));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * On click move to next attachment.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickNext: function (ev) {
        ev.preventDefault();
        var index = _.findIndex(this.attachments, this.activeAttachment);
        index = index === this.attachments.length -1 ? 0 : index + 1;
        this.activeAttachment = this.attachments[index];
        this._renderAttachment();
    },
    /**
     * On click move to previous attachment.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPrevious: function (ev) {
        ev.preventDefault();
        var index = _.findIndex(this.attachments, this.activeAttachment);
        index = index === 0 ? this.attachments.length - 1 : index - 1;
        this.activeAttachment = this.attachments[index];
        this._renderAttachment();
    },
});

return AttachmentViewer;
});
