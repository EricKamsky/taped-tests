# taped-tests
RQ based implementation of distributed django test runner.


### Warning `tapepd-tests` under development and not stable yet. Currently supports no-DB tests only

---

## Requirements

Taped tests work using `django-rq` thus `redis` server and pip package `django-rq` required.

## Usage

Extend settings with

```#!python
INSTALLED_APPS += ['django_rq', 'taped_tests']

TEST_RUNNER = 'taped_tests.runner.TapedTestSuiteRunner'

RQ_QUEUES = {
    # Define tests QUEUE
    'test': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
    }
}
```

Running tests becomes 2 step process:
 - start workers
   `./manage.py rqworker test` increasing workers count will speedup process

 - run tests as usual
   `./manage.py test`

---

# TODO:
 - Use settings to override queue names
 - Add database manipulation logic to RQ workers
 - Add more details
