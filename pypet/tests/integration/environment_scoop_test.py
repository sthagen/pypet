__author__ = 'robert'

import copy as cp
import sys

try:
    import scoop
    import random
except ImportError:
    scoop = None


def identity(x):
    return x


def check_mock():
    if scoop.IS_RUNNING:
        print('SCOOP mode functional!')
        mock = False
    else:
        mock = True
    return mock


class SharedMock(object):
    def __init__(self):
        self.constants = {}
        self.signal = True

    def mock(self):
        scoop.IS_ORIGIN = True
        scoop.worker = 'itsmemario'
        scoop.shared = self

    def setConst(self, **kwargs):
        if self.signal:
            print('NO SCOOP mode, mocking setConst!')
            self.signal = False
        self.constants.update(cp.deepcopy(kwargs))

    def getConst(self, const, timeout):
        return cp.deepcopy(self.constants[const])

# class ScoopFuturesWrapper(object):
#
#     def __init__(self):
#         self.signal = True  # to only print check mock once!
#
#     def check_mock(self):
#         try:
#             list(original_futures.map_as_completed(identity, [1,2,3]))
#             if self.signal:
#                 print('SCOOP mode functional!')
#             mock = False
#         except Exception:
#             if self.signal:
#                 print('Not started in SCOOP mode, I will MOCK scoop futures!')
#             mock = True
#         if self.signal:
#             self.signal = False
#         return mock
#
#     def mock_map_as_completed(self, func, iterator):
#         results = list(map(func, iterator))
#         return results
#
#     def map_as_completed(self, func, iterator):
#         mock = self.check_mock()
#         if mock:
#             return self.mock_map_as_completed(func, iterator)
#         else:
#             return original_futures.map_as_completed(func, iterator)
#
#     def __getattr__(self, item):
#         return getattr(original_futures, item)
#
#     def __setattr__(self, key, value):
#         setattr(original_futures, key, value)
#
#
# if scoop is not None:
#     scoop.futures = ScoopFuturesWrapper()

import pypet.environment

if check_mock():
    shared_mock = SharedMock()
    shared_mock.mock()
    # Reload to replace futures
    try:
        reload(pypet.environment)
    except NameError:
        # Python 3
        import importlib
        importlib.reload(pypet.environment)

from pypet.tests.integration.environment_test import EnvironmentTest, ResultSortTest
from pypet.tests.integration.environment_multiproc_test import check_nice
import pypet.pypetconstants as pypetconstants
from pypet.tests.testutils.ioutils import parse_args, run_suite
from pypet.tests.testutils.data import unittest


@unittest.skipIf(scoop is None, 'Only makes sense if scoop is installed')
class MultiprocSCOOPLocalTest(EnvironmentTest):

    tags = 'integration', 'hdf5', 'environment', 'multiproc', 'local', 'scoop'

    def set_mode(self):
        super(MultiprocSCOOPLocalTest, self).set_mode()
        self.mode = pypetconstants.WRAP_MODE_LOCAL
        self.multiproc = True
        self.freeze_input = False
        self.ncores = 4
        self.gc_interval = 3
        self.niceness = check_nice(1)
        self.use_pool=False
        self.use_scoop=True


    @unittest.skip('Does not work with scoop (fully), because scoop uses main frame.')
    def test_niceness(self):
        pass

    # def test_run(self):
    #     return super(MultiprocSCOOPLocalTest, self).test_run()

@unittest.skipIf(scoop is None, 'Only makes sense if scoop is installed')
class MultiprocSCOOPSortLocalTest(ResultSortTest):

    tags = 'integration', 'hdf5', 'environment', 'multiproc', 'local', 'scoop'

    def set_mode(self):
        super(MultiprocSCOOPSortLocalTest, self).set_mode()
        self.mode = pypetconstants.WRAP_MODE_LOCAL
        self.freeze_input = False
        self.multiproc = True
        self.ncores = 4
        self.use_pool=False
        self.use_scoop=True




@unittest.skipIf(scoop is None, 'Only makes sense if scoop is installed')
class MultiprocFrozenSCOOPLocalTest(EnvironmentTest):

    tags = 'integration', 'hdf5', 'environment', 'multiproc', 'local', 'scoop', 'freeze_input'

    def set_mode(self):
        super(MultiprocFrozenSCOOPLocalTest, self).set_mode()
        self.mode = pypetconstants.WRAP_MODE_LOCAL
        self.multiproc = True
        self.freeze_input = True
        self.ncores = 4
        self.gc_interval = 3
        self.niceness = check_nice(1)
        self.use_pool=False
        self.use_scoop=True


    @unittest.skip('Does not work with scoop (fully), because scoop uses main frame.')
    def test_niceness(self):
        pass

    # def test_run(self):
    #     return super(MultiprocSCOOPLocalTest, self).test_run()

@unittest.skipIf(scoop is None, 'Only makes sense if scoop is installed')
class MultiprocFrozenSCOOPSortLocalTest(ResultSortTest):

    tags = 'integration', 'hdf5', 'environment', 'multiproc', 'local', 'scoop', 'freeze_input'

    def set_mode(self):
        super(MultiprocFrozenSCOOPSortLocalTest, self).set_mode()
        self.mode = pypetconstants.WRAP_MODE_LOCAL
        self.freeze_input = True
        self.multiproc = True
        self.ncores = 4
        self.use_pool=False
        self.use_scoop=True


if __name__ == '__main__':
    opt_args = parse_args()
    run_suite(**opt_args)
