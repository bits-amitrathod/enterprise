# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import get_records_pager, CustomerPortal
from odoo.addons.website_form.controllers.main import WebsiteForm
from odoo.osv.expression import OR


class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        user = request.env.user
        values['ticket_count'] = request.env['helpdesk.ticket'].sudo().search_count(['|', ('user_id', '=', user.id), ('partner_id', '=', user.partner_id.id)])
        return values

    @http.route(['/my/tickets', '/my/tickets/page/<int:page>'], type='http', auth="user", website=True)
    def my_helpdesk_tickets(self, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        domain = ['|', ('user_id', '=', user.id), ('partner_id', '=', user.partner_id.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Subject'), 'order': 'name'},
        }
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'customer': {'input': 'customer', 'label': _('Search in Customer')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('helpdesk.ticket', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, ['|', ('name', 'ilike', search), ('description', 'ilike', search)]])
            if search_in in ('customer', 'all'):
                search_domain = OR([search_domain, [('partner_id', 'ilike', search)]])
            if search_in in ('message', 'all'):
                search_domain = OR([search_domain, [('message_ids.body', 'ilike', search)]])
            domain += search_domain

        # pager
        tickets_count = request.env['helpdesk.ticket'].search_count(domain)
        pager = request.website.pager(
            url="/my/tickets",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=tickets_count,
            page=page,
            step=self._items_per_page
        )

        tickets = request.env['helpdesk.ticket'].sudo().search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_tickets_history'] = tickets.ids[:100]

        values.update({
            'date': date_begin,
            'tickets': tickets,
            'page_name': 'ticket',
            'default_url': '/my/tickets',
            'pager': pager,
            'archive_groups': archive_groups,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'sortby': sortby,
            'search_in': search_in,
            'search': search,
        })
        return request.render("website_helpdesk.portal_helpdesk_ticket", values)


class WebsiteForm(WebsiteForm):

    def get_helpdesk_team_data(self, team, search=None):
        return {'team': team}

    @http.route(['/helpdesk/', '/helpdesk/<model("helpdesk.team"):team>'], type='http', auth="public", website=True)
    def website_helpdesk_teams(self, team=None, **kwargs):
        search = kwargs.get('search')
        # For breadcrumb index: get all team
        teams = request.env['helpdesk.team'].search(['|', '|', ('use_website_helpdesk_form', '=', True), ('use_website_helpdesk_forum', '=', True), ('use_website_helpdesk_slides', '=', True)], order="id asc")
        if not request.env.user.has_group('helpdesk.group_helpdesk_manager'):
            teams = teams.filtered(lambda team: team.website_published)
        if not teams:
            return request.render("website_helpdesk.not_published_any_team")
        result = self.get_helpdesk_team_data(team or teams[0], search=search)
        # For breadcrumb index: get all team
        result['teams'] = teams
        return request.render("website_helpdesk.team", result)

    @http.route([
        "/helpdesk/ticket/<int:ticket_id>",
        "/helpdesk/ticket/<int:ticket_id>/<token>"
    ], type='http', auth="public", website=True)
    def tickets_followup(self, ticket_id, token=None):
        Ticket = False
        if token:
            Ticket = request.env['helpdesk.ticket'].sudo().search([('id', '=', ticket_id), ('access_token', '=', token)])
        else:
            Ticket = request.env['helpdesk.ticket'].browse(ticket_id)
        if not Ticket:
            return request.render('website.404')
        values = {'ticket': Ticket}
        history = request.session.get('my_tickets_history', [])
        values.update(get_records_pager(history, Ticket))
        return request.render("website_helpdesk.tickets_followup", values)


class WebsiteHelpdesk(http.Controller):

    @http.route(['/helpdesk/rating/'], type='http', auth="public", website=True)
    def index(self, **kw):
        teams = request.env['helpdesk.team'].sudo().search([('use_rating', '=', True), ('use_website_helpdesk_rating', '=', True)])
        values = {'teams': teams}
        return request.render('website_helpdesk.index', values)

    @http.route(['/helpdesk/rating/<model("helpdesk.team"):team>'], type='http', auth="public", website=True)
    def page(self, team, project_id=None, **kw):
        user = request.env.user
        # to avoid giving any access rights on helpdesk team to the public user, let's use sudo
        # and check if the user should be able to view the team (team managers only if it's not published or has no rating)
        if not (team.use_rating and team.use_website_helpdesk_rating) and not user.sudo(user).has_group('helpdesk.group_helpdesk_manager'):
            raise NotFound()
        tickets = request.env['helpdesk.ticket'].sudo().search([('team_id', '=', team.id)])
        domain = [('res_model', '=', 'helpdesk.ticket'), ('res_id', 'in', tickets.ids)]
        ratings = request.env['rating.rating'].search(domain, order="id desc", limit=100)

        yesterday = (datetime.date.today()-datetime.timedelta(days=-1)).strftime('%Y-%m-%d 23:59:59')
        stats = {}
        for x in (7, 30, 90):
            todate = (datetime.date.today()-datetime.timedelta(days=x)).strftime('%Y-%m-%d 00:00:00')
            domdate = domain + [('create_date', '<=', yesterday), ('create_date', '>=', todate)]
            stats[x] = {1: 0, 5: 0, 10: 0}
            rating_stats = request.env['rating.rating'].read_group(domdate, [], ['rating'])
            total = sum(st['rating_count'] for st in rating_stats)
            for rate in rating_stats:
                stats[x][rate['rating']] = (rate['rating_count'] * 100) / total
        values = {
            'team': team,
            'ratings': ratings,
            'stats': stats,
        }
        return request.render('website_helpdesk.team_rating_page', values)
