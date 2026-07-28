import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
loader = unittest.TestLoader()
suite = loader.discover(os.path.dirname(os.path.abspath(__file__)), pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
