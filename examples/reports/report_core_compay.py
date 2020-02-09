# -*- coding: utf-8 -*-
import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler

from examples.factors.fundamental_selector import FundamentalSelector
from zvdata.api import get_entities
from zvdata.utils.time_utils import now_pd_timestamp
from zvt import init_log
from zvt.domain import Stock, StockTradeDay, FinanceFactor, BalanceSheet
from zvt.factors.target_selector import TargetSelector
from zvt.informer.informer import EmailInformer

logger = logging.getLogger(__name__)

sched = BackgroundScheduler()


@sched.scheduled_job('cron', hour=16, minute=0, day='15')
def report_core_company():
    while True:
        error_count = 0
        email_action = EmailInformer()

        try:
            Stock.record_data(provider='eastmoney')
            Stock.record_data(provider='joinquant')
            FinanceFactor.record_data(provider='eastmoney')
            BalanceSheet.record_data(provider='eastmoney')

            latest_day: StockTradeDay = StockTradeDay.query_data(order=StockTradeDay.timestamp.desc(), limit=1,
                                                                 return_type='domain')
            if latest_day:
                target_date = latest_day[0].timestamp
            else:
                target_date = now_pd_timestamp()

            my_selector: TargetSelector = FundamentalSelector(start_timestamp='2015-01-01', end_timestamp=target_date)
            my_selector.run()

            long_targets = my_selector.get_open_long_targets(timestamp=target_date)
            if long_targets:
                stocks = get_entities(provider='joinquant', entity_schema=Stock, entity_ids=long_targets,
                                      return_type='domain')
                info = [f'{stock.name}({stock.code})' for stock in stocks]
                msg = ' '.join(info)
            else:
                msg = 'no targets'

            logger.info(msg)

            email_action.send_message("5533061@qq.com", f'{target_date} 均线选股结果', msg)

            break
        except Exception as e:
            logger.exception('report1 sched error:{}'.format(e))
            time.sleep(60 * 3)
            error_count = error_count + 1
            if error_count == 10:
                email_action.send_message("5533061@qq.com", f'report ma targets error',
                                          'report1 sched error:{}'.format(e))


if __name__ == '__main__':
    init_log('report1.log')

    report_core_company()

    sched.start()

    sched._thread.join()
