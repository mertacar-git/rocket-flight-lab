import unittest
from core import Parameters,simulate,summary,validate_curve,atmosphere

class RocketTests(unittest.TestCase):
    def test_no_thrust(self):
        self.assertEqual(summary(simulate(Parameters(thrust_n=0,duration_s=5)))['apogee_m'],0)
    def test_mass_floor(self):
        rows=simulate()
        self.assertGreaterEqual(min(r['mass_kg'] for r in rows),1.0)
        self.assertEqual(rows[-1]['mass_kg'],1.0)
    def test_landing(self):
        result=summary(simulate())
        self.assertTrue(result['landed'])
        self.assertGreater(result['landing_time_s'],result['apogee_time_s'])
    def test_timestep_convergence(self):
        coarse=summary(simulate())['apogee_m']
        fine=summary(simulate(Parameters(dt_s=0.01)))['apogee_m']
        self.assertLess(abs(coarse-fine),0.2)
    def test_constant_mass_no_drag(self):
        # Constant-mass analytic powered ascent: h = a*t²/2.
        rows=simulate(Parameters(propellant_kg=0,drag_coefficient=0,burn_s=10,duration_s=2))
        expected=(35-9.80665)*2**2/2
        self.assertAlmostEqual(rows[-1]['altitude_m'],expected,delta=0.01)
    def test_invalid(self):
        with self.assertRaises(ValueError): simulate(Parameters(dry_mass_kg=0))
    def test_bad_curve(self):
        with self.assertRaises(ValueError): validate_curve([(0,10),(0,20)],3)
    def test_curve_equivalence(self):
        a=simulate(); b=simulate(curve=[(0,35),(3,35)])
        self.assertAlmostEqual(summary(a)['apogee_m'],summary(b)['apogee_m'],places=8)
    def test_atmosphere(self):
        self.assertLess(atmosphere(1000)[0],atmosphere(0)[0])
