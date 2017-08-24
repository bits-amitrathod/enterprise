# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

DISPLAY_FORMATS = {
    'day': '%d %b %Y',
    'week': 'W%W %Y',
    'month': '%B %Y',
    'year': '%Y',
}


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_cohort_data(self, date_start, date_stop, measure, interval, domain):
        rows = []
        columns_avg = defaultdict(lambda: dict(percentage=0, count=0))
        total_value = 0
        for group in self._read_group_raw(domain=domain, fields=[date_start], groupby=date_start + ':' + interval):
            dates = group['%s:%s' % (date_start, interval)]
            if not dates:
                continue
            clean_start_date = dates[0].split('/')[0].split(' ')[0]  # Split with space for smoothly format datetime field
            cohort_start_date = fields.Datetime.from_string(clean_start_date)

            records = self.search(group['__domain'])
            if measure == '__count__':
                value = float(len(records))
            else:
                value = float(sum([record[measure] for record in records]))
            total_value += value

            columns = []
            for col in range(0, 16):
                col_start_date = cohort_start_date
                if interval == 'day':
                    col_start_date += relativedelta(days=col)
                    col_end_date = col_start_date + relativedelta(days=1)
                elif interval == 'week':
                    col_start_date += relativedelta(days=7 * col)
                    col_end_date = col_start_date + relativedelta(days=7)
                elif interval == 'month':
                    col_start_date += relativedelta(months=col)
                    col_end_date = col_start_date + relativedelta(months=1)
                else:
                    col_start_date += relativedelta(years=col)
                    col_end_date = col_start_date + relativedelta(years=1)

                if col_start_date > datetime.today():
                    columns_avg[col]
                    columns.append({
                        'value': '-',
                        'percentage': '',
                    })
                    continue

                significative_period = col_start_date.strftime(DISPLAY_FORMATS[interval])
                col_records = [record for record in records if record[date_stop] and fields.Datetime.from_string(record[date_stop].split(' ')[0]).strftime(DISPLAY_FORMATS[interval]) == significative_period]

                if measure == '__count__':
                    col_value = len(col_records)
                else:
                    col_value = sum([record[measure] for record in col_records])

                previous_col_remaining_value = value if col == 0 else columns[-1]['value']
                col_remaining_value = previous_col_remaining_value - col_value
                percentage = value and round(100 * (col_remaining_value) / value, 1) or 0
                columns_avg[col]['percentage'] += percentage
                columns_avg[col]['count'] += 1
                columns.append({
                    'value': col_remaining_value,
                    'percentage': percentage,
                    'domain': [
                        (date_stop, ">=", col_start_date.strftime(DEFAULT_SERVER_DATE_FORMAT) ),
                        (date_stop, "<", col_end_date.strftime(DEFAULT_SERVER_DATE_FORMAT) ),
                    ]
                })

            rows.append({
                'date': dates[1],
                'value': value,
                'domain': group['__domain'],
                'columns': columns,
            })

        return {
            'rows': rows,
            'total': {'total_value': total_value, 'columns_avg': columns_avg},
        }
