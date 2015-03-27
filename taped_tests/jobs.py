import redis
from django_rq import job

import logging

try:
    import cPicle as pickle
except ImportError:
    import pickle

logger = logging.getLogger(__name__)


@job('test')
def test_job(testcase):
    result = testcase.defaultTestResult()

    logger.info('Invoking {}'.format(testcase))

    testcase.run(result)

    logger.info('Test result: {}'.format(result))

    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    r.publish('test-results', pickle.dumps(result,
                                           protocol=pickle.HIGHEST_PROTOCOL))
