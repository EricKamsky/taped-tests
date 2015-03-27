import sys
import time
import logging
import redis
from django.test.runner import DiscoverRunner

from unittest.runner import TextTestResult
from unittest.runner import _WritelnDecorator

try:
    import cPicle as pickle
except ImportError:
    import pickle


logger = logging.getLogger(__name__)

from taped_tests.jobs import test_job


class TapedTestSuiteRunner(DiscoverRunner):
    """
    Taped test suite runner.

    Runs tests using RQ workers
    allowing tests to be distributed across multiple processes/instances.
    """

    def __init__(self, *args, **kwargs):
        super(TapedTestSuiteRunner, self).__init__(*args, **kwargs)
        self.stream = _WritelnDecorator(sys.stdout)

    def run_suite(self, suite, **kwargs):
        """
        Enqueues all tests `settings.TAPED_TESTS_QUEUE` (defaults to 'test').
        """
        for test in suite:
            logger.info(test)
            test_job.delay(test)

        return object()

    def suite_result(self, suite, *args, **kwargs):
        """
        Fetches suite result from `settings.TAPED_TESTS_RESULTS` channel
        defaults to `test-results`.
        """
        startTime = time.time()

        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        p = r.pubsub(ignore_subscribe_messages=True)
        p.subscribe('test-results')

        test_results = []

        final = TextTestResult(self.stream, [], 1)

        while len(test_results) < len(suite._tests):
            message = p.get_message()
            if message:
                result = pickle.loads(message.get('data'))
                final = self.merge_results(final, result)

                printable = 's' if len(result.skipped) else '.'
                if not result.wasSuccessful():
                    if len(result.errors):
                        printable = 'e'
                    elif len(result.failures):
                        printable = 'f'
                self.stream.write(printable)

                test_results.append(result)
            time.sleep(0.001)

        stopTime = time.time()

        self.stream.writeln()

        logger.info(final.failures)

        self.print_result(final, stopTime - startTime)
        return final

    def print_result(self, result, time_taken):
        """
        Writes result details into sys.stdout
        """
        if hasattr(result, 'separator2'):
            self.stream.writeln(result.separator2)

        result.printErrors()

        if hasattr(result, 'separator2'):
            self.stream.writeln(result.separator2)
        run = result.testsRun
        self.stream.writeln("Ran %d test%s in %.3fs" %
                            (run, run != 1 and "s" or "", time_taken))
        self.stream.writeln()

        expectedFails = unexpectedSuccesses = skipped = 0
        try:
            results = map(len, (result.expectedFailures,
                                result.unexpectedSuccesses,
                                result.skipped))
        except AttributeError:
            pass
        else:
            expectedFails, unexpectedSuccesses, skipped = results

        infos = []
        if not result.wasSuccessful():
            self.stream.write("FAILED")
            failed, errored = map(len, (result.failures, result.errors))
            if failed:
                infos.append("failures=%d" % failed)
            if errored:
                infos.append("errors=%d" % errored)
        else:
            self.stream.write("OK")
        if skipped:
            infos.append("skipped=%d" % skipped)
        if expectedFails:
            infos.append("expected failures=%d" % expectedFails)
        if unexpectedSuccesses:
            infos.append("unexpected successes=%d" % unexpectedSuccesses)
        if infos:
            self.stream.writeln(" (%s)" % (", ".join(infos),))
        else:
            self.stream.write("\n")
        return result

    def merge_results(self, final, result):
        """
        Updates final result with information from one test result
        """
        final.errors += result.errors
        final.failures += result.failures
        final.skipped += result.skipped
        final.expectedFailures += result.expectedFailures
        final.unexpectedSuccesses += result.unexpectedSuccesses
        return final
