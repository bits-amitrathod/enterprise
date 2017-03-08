odoo.define('web_grid.GridView', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var core = require('web.core');
var GridModel = require('web_grid.GridModel');
var GridController = require('web_grid.GridController');
var GridRenderer = require('web_grid.GridRenderer');
var viewRegistry = require('web.view_registry');

var _lt = core._lt;

var GridView = AbstractView.extend({
    display_name: _lt('Grid'),
    icon: 'fa-tasks',
    config: {
        Model: GridModel,
        Controller: GridController,
        Renderer: GridRenderer,
    },
    init: function (arch, fields, params) {
        var self = this;
        this._super.apply(this, arguments);
        var rowFields = [];
        var colField, cellField, ranges, cellWidget;
        _.each(arch.children, function (child) {
            if (child.tag === 'field') {
                if (child.attrs.type === 'row') {
                    rowFields.push(child.attrs.name);
                }
                if (child.attrs.type === 'col') {
                    colField = child.attrs.name;
                    ranges = _.pluck(child.children, 'attrs');
                }
                if (child.attrs.type === 'measure') {
                    cellField = child.attrs.name;
                    cellWidget = child.attrs.widget;
                }
            }
        });


        // model
        this.loadParams.ranges = ranges;
        this.loadParams.currentRange = ranges[0];
        this.loadParams.rowFields = rowFields;
        this.loadParams.colField = colField;
        this.loadParams.cellField = cellField;

        // renderer
        this.rendererParams.canCreate = this.controllerParams.activeActions.create;
        this.rendererParams.fields = fields;
        this.rendererParams.noContentHelper = _.find(arch.children, function (c) {
            return c.tag === 'empty';
        });
        this.rendererParams.editableCells = this.controllerParams.activeActions.edit && arch.attrs.adjustment;
        this.rendererParams.cellWidget = cellWidget;

        // controller
        this.controllerParams.formViewID = false;
        this.controllerParams.listViewID = false;
        _.each(params.views, function (view) {
            if (view[1] === 'form') {
                self.controllerParams.formViewID = view[0];
            }
            if (view[1] === 'list') {
                self.controllerParams.listViewID = view[0];
            }
        });
        this.controllerParams.ranges = ranges;
        this.controllerParams.navigationButtons = arch.children
            .filter(function (c) { return c.tag === 'button'; })
            .map(function (c) { return c.attrs; });
        this.controllerParams.adjustment = arch.attrs.adjustment;
        this.controllerParams.adjustName = arch.attrs.adjust_name;
    },

});

viewRegistry.add('grid', GridView);

return GridView;
});



//         'blur .o_grid_input': function (e) {
//             var $target = $(e.target);

//             var data = this.get('grid_data');
//             // path should be [path, to, grid, 'grid', row_index, col_index]
//             var cell_path = $target.parent().attr('data-path').split('.');
//             var grid_path = cell_path.slice(0, -3);
//             var row_path = grid_path.concat(['rows'], cell_path.slice(-2, -1));
//             var col_path = grid_path.concat(['cols'], cell_path.slice(-1));

//             try {
//                 var val = this._cell_field.parse(e.target.textContent.trim());
//                 $target.removeClass('has-error');
//             } catch (_) {
//                 $target.addClass('has-error');
//                 return;
//             }

//             this.adjust({
//                 row: into(data, row_path),
//                 col: into(data, col_path),
//                 //ids: cell.ids,
//                 value: into(data, cell_path).value
//             }, val)
//         },
//         'focus .o_grid_input': function (e) {
//             var selection = window.getSelection();
//             var range = document.createRange();
//             range.selectNodeContents(e.target);
//             selection.removeAllRanges();
//             selection.addRange(range);
//         },
//     },


//     get_ids: function () {
//         var data = this.get('grid_data');
//         if (!_.isArray(data)) {
//             data = [data];
//         }

//         var domain = [];
//         // count number of non-empty cells and only add those to the search
//         // domain, on sparse grids this makes domains way smaller
//         var cells = 0;

//         for (var i = 0; i < data.length; i++) {
//             var grid = data[i].grid;

//             for (var j = 0; j < grid.length; j++) {
//                 var row = grid[j];
//                 for (var k = 0; k < row.length; k++) {
//                     var cell = row[k];
//                     if (cell.size != 0) {
//                         cells++;
//                         domain.push.apply(domain, cell.domain);
//                     }
//                 }
//             }
//         }

//         // if there are no elements in the grid we'll get an empty domain
//         // which will select all records of the model... that is *not* what
//         // we want
//         if (cells === 0) {
//             return $.when([]);
//         }

//         while (--cells > 0) {
//             domain.unshift('|');
//         }

//         return this._model.call('search', [domain], {context: this.get_full_context()})
//     },
//     get_full_context: function (ctx) {
//         var c = this._model.context(this.get('context'));
//         if (this.get('pagination_context')) {
//             c.add(this.get('pagination_context'));
//         }
//         // probably not ideal, needs to be kept in sync with arrows
//         if (this.get('range')) {
//             c.add({'grid_range': this.get('range')});
//         }
//         if (ctx) {
//             c.add(ctx);
//         }
//         return c;
//     },

//     do_search: function (domain, context, groupby) {
//         this.set({
//             'domain': domain,
//             'context': context,
//             'groupby': (groupby && groupby.length)
//                 ? groupby
//                 : this._archnodes_of_type('row').map(function (node) {
//                       return node.attrs.name;
//                   })
//         });
//         return this._fetch();
//     },
//     _fetch_section_grid: function (section_name, section_group, additional_context) {
//         return this._model.call('read_grid', {
//             row_fields: this.get('groupby').slice(1),
//             col_field: this._col_field.name(),
//             cell_field: this._cell_field.name(),
//             range: this.get('range') || false,
//             domain: section_group.__domain,
//             context: this.get_full_context(additional_context),
//         }).done(function (grid) {
//             grid.__label = section_group[section_name];
//         });
//     },
//     _fetch: function () {
//         // ignore if view hasn't been loaded yet
//         if (!this.fields_view || this.get('range') === undefined) {
//             return;
//         }
//         var _this = this;
//         var first_field = _this.get('groupby')[0];
//         var section = _(this.fields_view.arch.children).find(function (c) {
//             return c.tag === 'field'
//                 && c.attrs.name === first_field
//                 && c.attrs.type === 'row'
//                 && c.attrs.section === '1';
//         });

//         // FIXME: since enqueue can drop functions, what should the semantics be for it to return a promise?
//         this._enqueue(function () {
//             if (section) {
//                 var section_name = section.attrs.name;

//                 return _this._model.call('read_grid_domain', {
//                     field: _this._col_field.name(),
//                     range: _this.get('range') || false,
//                     context: _this.get_full_context(),
//                 }).then(function (d) {
//                     return _this._model.call('read_group', {
//                         domain: d.concat(_this.get('domain') || []),
//                         fields: [section_name],
//                         groupby: [section_name],
//                         context: _this.get_full_context()
//                     });
//                 }).then(function (groups) {
//                     if (!groups.length) {
//                         // if there are no groups in the output we still need
//                         // to fetch an empty grid so we can render the table's
//                         // decoration (pagination and columns &etc) otherwise
//                         // we get a completely empty grid
//                         return _this._fetch_section_grid(null, {
//                             __domain: _this.get('domain') || [],
//                         });
//                     }
//                     return $.when.apply(null, _(groups).map(function (group) {
//                         return _this._fetch_section_grid(section_name, group);
//                     }));
//                 }).then(function () {
//                     var results = [].slice.apply(arguments);
//                     var r0 = results[0];
//                     _this._navigation.set({
//                         prev: r0 && r0.prev,
//                         next: r0 && r0.next
//                     });
//                     _this.set('grid_data', results);
//                 });
//             }

//             return _this._model.call('read_grid', {
//                 row_fields: _this.get('groupby'),
//                 col_field: _this._col_field.name(),
//                 cell_field: _this._cell_field.name(),
//                 range: _this.get('range') || false,
//                 domain: _this.get('domain') || [],
//                 context: _this.get_full_context(),
//             }).then(function (results) {
//                 _this._navigation.set({
//                     prev: results.prev, next: results.next,
//                 });
//                 _this.set('grid_data', results);
//             });
//         });
//     },
//     _enqueue: function (fn) {
//         // We only want a single fetch being performed at any time (because
//         // there's really no point in performing 5 fetches concurrently just
//         // because the user has just edited 5 records), utils.Mutex does that
//         // fine, *however* we don't actually care about all the fetches, if
//         // we're enqueuing fetch n while fetch n-1 is waiting, we can just
//         // drop the older one, it's only going to delay the currently
//         // useful and interesting job.
//         //
//         // So when requesting a fetch
//         // * if there's no request waiting on the mutex (for a fetch to come
//         //   back) set the new request waiting and queue up a fetch on the
//         //   mutex
//         // * if there is already a request waiting (and thus an enqueued fetch
//         //   on the mutex) just replace the old request, so it'll get taken up
//         //   by the enqueued fetch eventually
//         var _this = this;
//         if (this._in_waiting) {
//             // if there's already a query waiting for a slot, drop it and replace
//             // it by the new updated query
//             this._in_waiting = fn;
//         } else {
//             // if there's no query waiting for a slot, add the current one and
//             // enqueue a fetch job
//             this._in_waiting = fn;
//             this._fetch_mutex.exec(function () {
//                 var fn = _this._in_waiting;
//                 _this._in_waiting = null;

//                 return fn();
//             })
//         }

//     },
//     _archnodes_of_type: function (type) {
//         return _.filter(this.fields_view.arch.children, function (c) {
//             return c.tag === 'field' && c.attrs.type === type;
//         });
//     },
//     _fields_of_type: function (type) {
//         return _(this._archnodes_of_type(type)).map(function (arch_f) {
//             var name = arch_f.attrs.name;
//             return this._make_field(name, arch_f);
//         }.bind(this));
//     },
// });
