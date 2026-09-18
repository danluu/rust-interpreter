"""Run the existing CFG contracts with the additional memory recognizer."""
import unittest
import test_cfg as reference
from cfg_memory import analyze_cfg
reference.analyze_cfg=analyze_cfg
Cfg=reference.Cfg
if __name__=='__main__':unittest.main()
