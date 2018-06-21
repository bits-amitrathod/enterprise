odoo.define('web_unsplash.image_widgets', function (require) {
'use strict';

var core = require('web.core');
var UnsplashAPI = require('unsplash.api');
var ImageWidget = require('web_editor.widget').ImageWidget;
var QWeb = core.qweb;

ImageWidget.include({
    xmlDependencies: ImageWidget.prototype.xmlDependencies.concat(
        ['/web_unsplash/static/src/xml/unsplash_image_widget.xml']
    ),
    events: _.extend({}, ImageWidget.prototype.events, {
        'input input.unsplash_search': '_onChangeUnsplashSearch',
        'dblclick .unsplash_img_container [data-imgid]': '_onUnsplashImgDblClick',
        'click .unsplash_img_container [data-imgid]': '_onUnsplashImgClick',
        'click button.access_key': '_onSetAccessKey',
    }),
    /**
     * @override
     */
    init: function () {
        this._unsplash = {
            selectedImages: {},
            isMaxed: false,
            query: false,
        };
        return this._super.apply(this, arguments);
    },

    // --------------------------------------------------------------------------
    // Public
    // --------------------------------------------------------------------------

    /**
     * @override
     */
    getControlPanelConfig: function () {
        var config = this._super.apply(this, arguments);
        if (this._unsplash.query) {
            _.extend(config, {
                pagerLeftEnabled: this.page > 1,
                pagerRightEnabled: !this._unsplash.isMaxed,
            });
        }
        return config;
    },
    /**
     * @override
     */
    save: function () {
        if (!this._unsplash.query) {
            return this._super.apply(this, arguments);
        }
        var self = this;
        var args = arguments;
        var _super = this._super;
        return this._rpc({
            route: '/web_unsplash/attachment/add',
            params: {
                unsplashurls: self._unsplash.selectedImages,
                res_model : self.options.res_model || "ir.ui.view",
                res_id: self.options.res_id,
            }
        }).then(function (images) {
            _.each(images, function (image) {
                image.src = _.str.sprintf('/web/image/%s', image.id);
                image.isDocument = !(/gif|jpe|jpg|png/.test(image.mimetype));
            });
            self.images = images;
            return _super.apply(self, args);
        });
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * use to highlight selected image on click and when pager change
     *
     * @private
     */
    _highlightSelectedImages: function () {
        var self = this;
        if (!this._unsplash.query) {
            return this._super.apply(this, arguments);
        }
        this.$('.o_unsplash_img_cell.o_selected').removeClass("o_selected");
        var $select = this.$('.o_unsplash_img_cell [data-imgid]').filter(function () {
            return $(this).data('imgid') in self._unsplash.selectedImages;
        });
        $select.closest('.o_unsplash_img_cell').addClass("o_selected");
        return $select;
    },
    /**
     * overriden this metod for separate rendering of unsplash images
     *
     * @override
     */
    _renderImages: function () {
        var self = this;
        if (!this._unsplash.query) {
            return this._super.apply(this, arguments);
        }
        UnsplashAPI.getImages(self._unsplash.query, this.IMAGES_PER_PAGE, this.page).then(function (res) {
            self._unsplash.isMaxed = res.isMaxed;
            self.$('.unsplash_img_container').html(QWeb.render('web_unsplash.dialog.image.content', { rows: res.images }));
            self._highlightSelectedImages();
        }).fail(function (err) {
            self.$('.unsplash_img_container').html(QWeb.render('web_unsplash.dialog.error.content', err));
        }).always(function () {
            self._toggleAttachmentContaines(false);
        });
    },
    /**
     * @private
     */
    _toggleAttachmentContaines: function (hideUnsplash) {
        this.$('.existing-attachments').toggleClass('o_hidden', !hideUnsplash);
        this.$('.unsplash_img_container').toggleClass('o_hidden', hideUnsplash);
        this.trigger_up('update_control_panel');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * @private
     */
    _onSetAccessKey: function () {
        var self = this;
        var key = this.$('#accessKeyInput').val().trim();
        if (key) {
            this._rpc({
                model: 'ir.config_parameter',
                method: 'set_param',
                args: ['unsplash.access_key', key],
            }).then(function () {
                UnsplashAPI.clientId = key;
                self._renderImages();
            });
        }
    },
    /**
     * @private
     */
    _onChangeUnsplashSearch: _.debounce(function () {
        this._unsplash.query = this.$('.unsplash_search').val().trim();
        if (this._unsplash.query) {
            this.oldPage = this.page;
            this.page = 1;
            this._renderImages();
        } else {
            this.page = this.oldPage || 0;
            this._toggleAttachmentContaines(true);
        }
    }, 1000),
    /**
     * @private
     */
    _onUnsplashImgClick: function (ev) {
        var imgid = $(ev.currentTarget).data('imgid');
        var url = $(ev.currentTarget).data('url');
        if (!this.multiImages) {
            this._unsplash.selectedImages = {};
        }
        if (imgid in this._unsplash.selectedImages) {
            delete this._unsplash.selectedImages[imgid];
        } else {
            this._unsplash.selectedImages[imgid] = url;
        }
        this._highlightSelectedImages();
    },
    /**
     * @private
     */
    _onUnsplashImgDblClick: function (ev) {
        this.trigger_up('save_request');
    },
});
});
