odoo.define('unsplash.core', function (require) {
'use strict';

var Class = require('web.Class');
var rpc = require('web.rpc');

var UnsplashCore = Class.extend({
    /**
     * @constructor
     */
    init: function () {
        this._catch = {};
        this.clientId = false;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * get unsplash images from query
     *
     * @public
     */
    getImages: function (query, pageSize, pageNumber) {
        var self = this;
        var to = pageSize * pageNumber;
        var from = to - pageSize;
        var cachedData = this._catch[query];

        if (cachedData && (cachedData.images.length >= to || (cachedData.totalImages !== 0 && cachedData.totalImages < to))) {
            return $.Deferred().resolve({ images: cachedData.images.slice(from, to), isMaxed: to > cachedData.totalImages });
        }
        return this._getAPIKey().then(function (clientID) {
            if (!clientID) {
                return $.Deferred().reject({ key_not_found: true });
            }
            return self._fetchImages(query).then(function (cachedData) {
                return { images: cachedData.images.slice(from, to), isMaxed: to > cachedData.totalImages };
            });
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * check and retrive unsplash api key
     *
     * @private
     */
    _getAPIKey: function () {
        var self = this;
        if (this.clientId) {
            return $.Deferred().resolve(self.clientId);
        }
        return rpc.query({
            model: 'ir.config_parameter',
            method: 'get_param',
            args: ['unsplash.access_key'],
        }).then(function (res) {
            self.clientId = res;
            return res;
        });
    },
    /**
     * fetch images from unsplash api and store in catch
     *
     * @private
     */
    _fetchImages: function (query) {
        if (!this._catch[query]) {
            this._catch[query] = {
                images: [],
                maxPages: 0,
                totalImages: 0,
                pageCached: 0
            };
        }
        var cachedData = this._catch[query];
        var payload = {
            query: query,
            page: cachedData.pageCached + 1,
            client_id: this.clientId,
            per_page: 30, // max size from unsplash API
        };
        return $.get('https://api.unsplash.com/search/photos/', payload).then(function (result) {
            cachedData.pageCached++;
            cachedData.images.push.apply(cachedData.images, result.results);
            cachedData.maxPages = result.total_pages;
            cachedData.totalImages = result.total;
            return cachedData;
        });
    },
});

return UnsplashCore;

});

odoo.define('unsplash.api', function (require) {
'use strict';

var UnsplashCore = require('unsplash.core');

return new UnsplashCore();

});
