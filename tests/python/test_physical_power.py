import unittest

from simulation.eda.physical_power import measured_components


class PhysicalPowerTests(unittest.TestCase):
    def test_decimal_and_scientific_power_components(self):
        report = ('*\tPower Units = 1mW\n'
                  'Total Internal Power: 1.5\n'
                  'Total Switching Power: 0.4\n'
                  'Total Leakage Power: 5.0e-03\n'
                  'Total Power: 1.905\n')
        self.assertEqual(measured_components(report)['leakage_mw'], 0.005)
        with self.assertRaisesRegex(ValueError, 'differs from'):
            measured_components(report.replace('1.905', '1.9'))
        with self.assertRaisesRegex(ValueError, 'specify mW'):
            measured_components(report.replace('1mW', '1W'))
