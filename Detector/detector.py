# coding:utf-8

"""
    @author  : linkin
    @email   : yooleak@outlook.com
    @date    : 2018-10-07
"""
import time
import gevent
import logging
from Helper.dbhelper    import Database
from DB.settings        import _DB_SETTINGS
from DB.settings        import _TABLE
from gevent             import pool
from gevent             import monkey
from config.config      import CONCURRENCY
from config.config      import DETECT_LOCAL
from config.config      import DETECT_AMOUNT
from config.config      import STABLE_MIN_RATE
from config.config      import STABLE_MIN_COUNT
from config.config      import DETECT_HIGH_AMOUNT

logger = logging.getLogger('Detector')

class Detector(object):
    """此模块没有进行pymysql支持"""
    def __init__(self):
        self.standbyDB  = Database(_DB_SETTINGS)
        self.stableDB   = Database(_DB_SETTINGS)
        self.standbyDB.table  = _TABLE['standby']
        self.stableDB.table   = _TABLE['stable']
        self.standby_data     = []
        self.stable_data      = []

    def begin(self):
        self.stableDB.connect()
        self.standbyDB.connect()

    def end(self):
        self.standbyDB.close()
        self.stableDB.close()

    def run(self):
        self.begin()
        while 1:
            try:
                self.detect_standby()
                self.detect_stable()
                time.sleep(DETECT_LOCAL)
            except Exception as e:
                logger.error('Error class : %s , msg : %s ' % (e.__class__, e))
                self.end()
                logger.info('Detector shuts down.')
                return

    def detect_standby(self):
        if self.standby_data:
            pen = len(self.standby_data)
            logger.info('Imported the standby database\' data,length: %d ' % pen)
            pop_len = pen if pen <= DETECT_AMOUNT else DETECT_AMOUNT
            logger.info('Start to detect the local valid data,amount: %d ' % pop_len)
            local_proxies = [self.standby_data.pop() for i in range(pop_len)]
            gpool = pool.Pool(CONCURRENCY)
            gevent.joinall([gpool.spawn(self._detect_standby, i) for i in local_proxies if i])
        else:
            self.standby_data = self.standbyDB.all()

    def detect_stable(self):
        if self.stable_data:
            pen = len(self.stable_data)
            logger.info('Imported the stable database\' data,length: %d ' % pen)
            pop_len = pen if pen <= DETECT_HIGH_AMOUNT else DETECT_HIGH_AMOUNT
            logger.info('Start to detect the high scored data,amount: %d ' % pop_len)
            local_proxies = [self.stable_data.pop() for i in range(pop_len)]
            gpool = pool.Pool(CONCURRENCY)
            gevent.joinall([gpool.spawn(self._detect_stable, i) for i in local_proxies if i])
        else:
            self.stable_data = self.stableDB.all()


    def _detect_standby(self,data):
        ip = data['ip']
        port = data['port']
        proxy = ':'.join([ip,port])
        del data['_id']
        if data['test_count']<STABLE_MIN_COUNT or data['success_rate'] < str(STABLE_MIN_RATE*100)+'%':
            return
        logger.info('Find a stable proxy: %s , putting it into the stable database.'%proxy)
        condition = {'ip':ip,'port':port}
        _one_data = self.stableDB.select(condition)
        if _one_data:
            self.stableDB.update(condition,data)
        else:
            self.stableDB.save(data)

    def _detect_stable(self,data):
        ip = data['ip']
        port = data['port']
        proxy = ':'.join([ip,port])
        del data['_id']
        condition = {'ip':ip,'port':port}
        _one_data = self.standbyDB.select(condition)
        if not bool(_one_data):
            self.stableDB.delete(condition)
            logger.warning(
                'The high scored proxy: %s had been deleted from the standby database.It\'s unavailable.' % proxy)











