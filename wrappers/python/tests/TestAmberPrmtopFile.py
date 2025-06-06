import unittest
import os
import tempfile
from validateConstraints import *
from openmm.app import *
from openmm import *
from openmm.unit import *
import openmm.app.element as elem

inpcrd1 = AmberInpcrdFile('systems/alanine-dipeptide-explicit.inpcrd')
inpcrd3 = AmberInpcrdFile('systems/ff14ipq.rst7')
inpcrd4 = AmberInpcrdFile('systems/Mg_water.inpcrd')
inpcrd7 = AmberInpcrdFile('systems/18protein.rst7')
prmtop1 = AmberPrmtopFile('systems/alanine-dipeptide-explicit.prmtop')
prmtop2 = AmberPrmtopFile('systems/alanine-dipeptide-implicit.prmtop')
prmtop3 = AmberPrmtopFile('systems/ff14ipq.parm7', periodicBoxVectors=inpcrd3.boxVectors)
prmtop4 = AmberPrmtopFile('systems/Mg_water.prmtop', periodicBoxVectors=inpcrd4.boxVectors)
prmtop5 = AmberPrmtopFile('systems/tz2.truncoct.parm7')
prmtop6 = AmberPrmtopFile('systems/gaffwat.parm7')
prmtop7 = AmberPrmtopFile('systems/18protein.parm7', periodicBoxVectors=inpcrd7.boxVectors)

class TestAmberPrmtopFile(unittest.TestCase):

    """Test the AmberPrmtopFile.createSystem() method."""

    def test_NonbondedMethod(self):
        """Test all six options for the nonbondedMethod parameter."""

        methodMap = {NoCutoff:NonbondedForce.NoCutoff,
                     CutoffNonPeriodic:NonbondedForce.CutoffNonPeriodic,
                     CutoffPeriodic:NonbondedForce.CutoffPeriodic,
                     Ewald:NonbondedForce.Ewald,
                     PME:NonbondedForce.PME,
                     LJPME:NonbondedForce.LJPME}
        for method in methodMap:
            system = prmtop1.createSystem(nonbondedMethod=method)
            forces = system.getForces()
            self.assertTrue(any(isinstance(f, NonbondedForce) and
                                f.getNonbondedMethod()==methodMap[method]
                                for f in forces))

    def test_Cutoff(self):
        """Test to make sure the nonbondedCutoff parameter is passed correctly."""

        for method in [CutoffNonPeriodic, CutoffPeriodic, Ewald, PME, LJPME]:
            system = prmtop1.createSystem(nonbondedMethod=method,
                                          nonbondedCutoff=2*nanometer,
                                          constraints=HBonds)
            cutoff_distance = 0.0*nanometer
            cutoff_check = 2.0*nanometer
            for force in system.getForces():
                if isinstance(force, NonbondedForce):
                    cutoff_distance = force.getCutoffDistance()
            self.assertEqual(cutoff_distance, cutoff_check)

    def test_EwaldErrorTolerance(self):
        """Test to make sure the ewaldErrorTolerance parameter is passed correctly."""

        for method in [Ewald, PME, LJPME]:
            system = prmtop1.createSystem(nonbondedMethod=method,
                                          ewaldErrorTolerance=1e-6,
                                          constraints=HBonds)
            tolerance = 0
            tolerance_check = 1e-6
            for force in system.getForces():
                if isinstance(force, NonbondedForce):
                    tolerance = force.getEwaldErrorTolerance()
            self.assertEqual(tolerance, tolerance_check)

    def test_RemoveCMMotion(self):
        """Test both options (True and False) for the removeCMMotion parameter."""

        for b in [True, False]:
            system = prmtop1.createSystem(removeCMMotion=b)
            forces = system.getForces()
            self.assertEqual(any(isinstance(f, CMMotionRemover) for f in forces), b)

    def test_RigidWaterAndConstraints(self):
        """Test all eight options for the constraints and rigidWater parameters."""

        topology = prmtop1.topology
        for constraints in [None, HBonds, AllBonds, HAngles]:
            for rigidWater in [True, False]:
                system = prmtop1.createSystem(constraints=constraints, rigidWater=rigidWater)
                if constraints != None:
                    # Amber adds an extra "bond" between water hydrogens, so any constraint
                    # method except None is equivalent to rigidWater=True.
                    rigidWater = True
                validateConstraints(self, topology, system, constraints, rigidWater)

    def test_ImplicitSolvent(self):
        """Test the four types of implicit solvents using the implicitSolvent
        parameter.

        """
        for implicitSolvent_value, gbsa in zip([HCT, OBC1, OBC2, GBn], ['ACE', None, 'ACE', None]):
            system = prmtop2.createSystem(implicitSolvent=implicitSolvent_value, gbsaModel=gbsa)
            forces = system.getForces()
            if implicitSolvent_value in set([HCT, OBC1, GBn]):
                force_type = CustomGBForce
            else:
                force_type = GBSAOBCForce

            self.assertTrue(any(isinstance(f, force_type) for f in forces))

    def test_ImplicitSolventParameters(self):
        """Test that parameters are set correctly for the different types of implicit solvent."""
        methodMap = {NoCutoff:NonbondedForce.NoCutoff,
                     CutoffNonPeriodic:NonbondedForce.CutoffNonPeriodic}
        for implicitSolvent_value in [HCT, OBC1, OBC2, GBn]:
            for method in methodMap:
                system = prmtop2.createSystem(implicitSolvent=implicitSolvent_value,
                                    solventDielectric=50.0, soluteDielectric=0.9, nonbondedMethod=method)
                if implicitSolvent_value in set([HCT, OBC1, GBn]):
                    for force in system.getForces():
                        if isinstance(force, CustomGBForce):
                            self.assertEqual(force.getNonbondedMethod(), methodMap[method])
                        if isinstance(force, NonbondedForce):
                            self.assertEqual(force.getReactionFieldDielectric(), 1.0)
                            self.assertEqual(force.getNonbondedMethod(), methodMap[method])
                else:
                    for force in system.getForces():
                        if isinstance(force, GBSAOBCForce):
                            self.assertEqual(force.getNonbondedMethod(), methodMap[method])
                            if force.getSolventDielectric() == 50.0:
                                found_matching_solvent_dielectric = True
                            if force.getSoluteDielectric() == 0.9:
                                found_matching_solute_dielectric = True
                        if isinstance(force, NonbondedForce):
                            self.assertEqual(force.getReactionFieldDielectric(), 1.0)
                            self.assertEqual(force.getNonbondedMethod(), methodMap[method])
                    self.assertTrue(found_matching_solvent_dielectric and
                                    found_matching_solute_dielectric)

    def test_ImplicitSolventZeroSA(self):
        """Test that requesting gbsaModel=None yields a surface area energy of 0 when 
           prmtop.createSystem produces a GBSAOBCForce"""
        system = prmtop2.createSystem(implicitSolvent=OBC2, gbsaModel=None)
        for force in system.getForces():
            if isinstance(force, GBSAOBCForce):
                self.assertEqual(force.getSurfaceAreaEnergy(), 0*kilojoule/(nanometer**2*mole))

    def test_HydrogenMass(self):
        """Test that altering the mass of hydrogens works correctly."""

        topology = prmtop1.topology
        hydrogenMass = 4*amu
        system1 = prmtop1.createSystem()
        system2 = prmtop1.createSystem(hydrogenMass=hydrogenMass)
        for atom in topology.atoms():
            if atom.element == elem.hydrogen:
                self.assertNotEqual(hydrogenMass, system1.getParticleMass(atom.index))
                if atom.residue.name == 'HOH':
                    self.assertEqual(system1.getParticleMass(atom.index), system2.getParticleMass(atom.index))
                else:
                    self.assertEqual(hydrogenMass, system2.getParticleMass(atom.index))
        totalMass1 = sum([system1.getParticleMass(i) for i in range(system1.getNumParticles())]).value_in_unit(amu)
        totalMass2 = sum([system2.getParticleMass(i) for i in range(system2.getNumParticles())]).value_in_unit(amu)
        self.assertAlmostEqual(totalMass1, totalMass2)

    def test_NBFIX_LongRange(self):
        """Test prmtop files with NBFIX LJ modifications w/ long-range correction"""
        system = prmtop3.createSystem(nonbondedMethod=PME,
                                      nonbondedCutoff=8*angstroms)
        # Check the forces
        has_nonbond_force = has_custom_nonbond_force = False
        nonbond_exceptions = custom_nonbond_exclusions = 0
        for force in system.getForces():
            if isinstance(force, NonbondedForce):
                has_nonbond_force = True
                nonbond_exceptions = force.getNumExceptions()
            elif isinstance(force, CustomNonbondedForce):
                has_custom_nonbond_force = True
                custom_nonbond_exceptions = force.getNumExclusions()
        self.assertTrue(has_nonbond_force)
        self.assertTrue(has_custom_nonbond_force)
        self.assertEqual(nonbond_exceptions, custom_nonbond_exceptions)
        integrator = VerletIntegrator(1.0*femtoseconds)
        # Use reference platform, since it should always be present and
        # 'working', and the system is plenty small so this won't be too slow
        sim = Simulation(prmtop3.topology, system, integrator, Platform.getPlatform('Reference'))
        # Check that the energy is about what we expect it to be
        sim.context.setPositions(inpcrd3.positions)
        ene = sim.context.getState(getEnergy=True, enforcePeriodicBox=True).getPotentialEnergy()
        ene = ene.value_in_unit(kilocalories_per_mole)
        # Make sure the energy is relatively close to the value we get with
        # Amber using this force field.
        self.assertAlmostEqual(-7099.44989739/ene, 1, places=3)

    def test_NBFIX_noLongRange(self):
        """Test prmtop files with NBFIX LJ modifications w/out long-range correction"""
        system = prmtop3.createSystem(nonbondedMethod=PME,
                                      nonbondedCutoff=8*angstroms)
        # Check the forces
        has_nonbond_force = has_custom_nonbond_force = False
        nonbond_exceptions = custom_nonbond_exclusions = 0
        for force in system.getForces():
            if isinstance(force, NonbondedForce):
                has_nonbond_force = True
                nonbond_exceptions = force.getNumExceptions()
            elif isinstance(force, CustomNonbondedForce):
                has_custom_nonbond_force = True
                custom_nonbond_exceptions = force.getNumExclusions()
                force.setUseLongRangeCorrection(False)
        self.assertTrue(has_nonbond_force)
        self.assertTrue(has_custom_nonbond_force)
        self.assertEqual(nonbond_exceptions, custom_nonbond_exceptions)
        integrator = VerletIntegrator(1.0*femtoseconds)
        # Use reference platform, since it should always be present and
        # 'working', and the system is plenty small so this won't be too slow
        sim = Simulation(prmtop3.topology, system, integrator, Platform.getPlatform('Reference'))
        # Check that the energy is about what we expect it to be
        sim.context.setPositions(inpcrd3.getPositions())
        ene = sim.context.getState(getEnergy=True, enforcePeriodicBox=True).getPotentialEnergy()
        ene = ene.value_in_unit(kilocalories_per_mole)
        # Make sure the energy is relatively close to the value we get with
        # Amber using this force field.
        self.assertAlmostEqual(-7042.3903307/ene, 1, places=3)

    def test_HAngle(self):
        """ Test that HAngle constraints are properly handled for all hydrogens """
        system = prmtop6.createSystem(nonbondedMethod=PME,
                                      nonbondedCutoff=1*nanometers,
                                      constraints=HBonds)
        self.assertEqual(system.getForce(0).getNumBonds(), 0)
        self.assertEqual(system.getNumParticles(), 3000)
        self.assertEqual(system.getNumConstraints(), 2000)
        self.assertEqual(system.getForce(1).getNumAngles(), 1000)

        system = prmtop6.createSystem(nonbondedMethod=PME,
                                      nonbondedCutoff=1*nanometers,
                                      constraints=HAngles)
        self.assertEqual(system.getForce(0).getNumBonds(), 0)
        self.assertEqual(system.getNumParticles(), 3000)
        self.assertEqual(system.getNumConstraints(), 3000)
        self.assertEqual(system.getForce(1).getNumAngles(), 0)

    def test_LJ1264(self):
        """Test prmtop with 12-6-4 vdW potential implemented"""
        system = prmtop4.createSystem(nonbondedMethod=PME,
                                      nonbondedCutoff=8*angstroms)
        # Check the forces
        has_nonbond_force = has_custom_nonbond_force = False
        nonbond_exceptions = custom_nonbond_exclusions = 0
        for force in system.getForces():
            if isinstance(force, NonbondedForce):
                has_nonbond_force = True
                nonbond_exceptions = force.getNumExceptions()
                force.setUseDispersionCorrection(False)
            elif isinstance(force, CustomNonbondedForce):
                self.assertTrue(force.getUseLongRangeCorrection())
                has_custom_nonbond_force = True
                custom_nonbond_exceptions = force.getNumExclusions()
                force.setUseLongRangeCorrection(False)
        self.assertTrue(has_nonbond_force)
        self.assertTrue(has_custom_nonbond_force)
        self.assertEqual(nonbond_exceptions, custom_nonbond_exceptions)
        # Make sure the periodic box vectors match the ones in the inpcrd file, which are different from
        # the ones in the prmtop file.
        systemBox = system.getDefaultPeriodicBoxVectors()
        topologyBox = prmtop4.topology.getPeriodicBoxVectors()
        for i in range(3):
            for j in range(3):
                self.assertEqual(inpcrd4.boxVectors[i][j], systemBox[i][j])
                self.assertEqual(inpcrd4.boxVectors[i][j], topologyBox[i][j])
        integrator = VerletIntegrator(1.0*femtoseconds)
        # Use reference platform, since it should always be present and
        # 'working', and the system is plenty small so this won't be too slow
        sim = Simulation(prmtop4.topology, system, integrator, Platform.getPlatform('Reference'))
        # Check that the energy is about what we expect it to be
        sim.context.setPositions(inpcrd4.positions)
        ene = sim.context.getState(getEnergy=True, enforcePeriodicBox=True).getPotentialEnergy()
        ene = ene.value_in_unit(kilocalories_per_mole)
        # Make sure the energy is relatively close to the value we get with
        # Amber using this force field.
        self.assertAlmostEqual(-7307.2735621/ene, 1, places=3)

    def test_triclinicParm(self):
        """ Check that triclinic unit cells work correctly """
        system = prmtop5.createSystem(nonbondedMethod=PME)
        refa = Vec3(4.48903851, 0.0, 0.0) * nanometer
        refb = Vec3(-1.4963460492639706, 4.232306137924705, 0.0) * nanometer
        refc = Vec3(-1.4963460492639706, -2.116152812842565, 3.6652847799064165) * nanometer
        a, b, c = system.getDefaultPeriodicBoxVectors()
        la = norm(a)
        lb = norm(b)
        lc = norm(c)
        diffa = a - refa
        diffb = b - refb
        diffc = c - refc
        self.assertAlmostEqual(norm(diffa)/nanometers, 0)
        self.assertAlmostEqual(norm(diffb)/nanometers, 0)
        self.assertAlmostEqual(norm(diffc)/nanometers, 0)
        self.assertAlmostEqual(dot(a, b)/la/lb, cos(109.4712190*degrees))
        self.assertAlmostEqual(dot(a, c)/la/lc, cos(109.4712190*degrees))
        self.assertAlmostEqual(dot(c, b)/lc/lb, cos(109.4712190*degrees))
        self.assertAlmostEqual(la/nanometers, 4.48903851)
        self.assertAlmostEqual(lb/nanometers, 4.48903851)
        self.assertAlmostEqual(lc/nanometers, 4.48903851)
        # Now make sure that the context builds correctly; then we can bail
        self.assertTrue(Context(system, VerletIntegrator(1*femtoseconds)))

    def test_ImplicitSolventForces(self):
        """Compute forces for different implicit solvent types, and compare them to ones generated with a previous version of OpenMM to ensure they haven't changed."""

        solventType = [HCT, OBC1, OBC2, GBn, GBn2]
        nonbondedMethod = [NoCutoff, CutoffNonPeriodic, CutoffNonPeriodic, NoCutoff, NoCutoff]
        salt = [0.0, 0.0, 0.5, 0.5, 0.0]*(moles/liter)
        file = ['HCT_NoCutoff', 'OBC1_NonPeriodic', 'OBC2_NonPeriodic_Salt', 'GBn_NoCutoff_Salt', 'GBn2_NoCutoff']
        pdb = PDBFile('systems/alanine-dipeptide-implicit.pdb')
        for i in range(5):
            system = prmtop2.createSystem(implicitSolvent=solventType[i], nonbondedMethod=nonbondedMethod[i], implicitSolventSaltConc=salt[i])
            integrator = VerletIntegrator(0.001)
            context = Context(system, integrator, Platform.getPlatform("Reference"))
            context.setPositions(pdb.positions)
            state1 = context.getState(getForces=True)
            with open('systems/alanine-dipeptide-implicit-forces/'+file[i]+'.xml') as infile:
                state2 = XmlSerializer.deserialize(infile.read())
            for f1, f2, in zip(state1.getForces().value_in_unit(kilojoules_per_mole/nanometer), state2.getForces().value_in_unit(kilojoules_per_mole/nanometer)):
                diff = norm(f1-f2)
                self.assertTrue(diff < 0.1 or diff/norm(f1) < 1e-4)

    def testSwitchFunction(self):
        """ Tests the switching function option in AmberPrmtopFile """
        system = prmtop1.createSystem(nonbondedMethod=PME,
                                      nonbondedCutoff=1*nanometer,
                                      switchDistance=0.8*nanometer)
        for force in system.getForces():
            if isinstance(force, NonbondedForce):
                self.assertTrue(force.getUseSwitchingFunction())
                self.assertEqual(force.getSwitchingDistance(), 0.8*nanometer)
                break
        else:
            assert False, 'Did not find expected nonbonded force!'

        # Check error handling
        system = prmtop1.createSystem(nonbondedMethod=PME,
                                      nonbondedCutoff=1*nanometer)
        for force in system.getForces():
            if isinstance(force, NonbondedForce):
                self.assertFalse(force.getUseSwitchingFunction())
                break
        else:
            assert False, 'Did not find expected nonbonded force!'

        self.assertRaises(ValueError, lambda:
                prmtop1.createSystem(nonbondedMethod=PME,
                    nonbondedCutoff=1*nanometer, switchDistance=-1)
        )
        self.assertRaises(ValueError, lambda:
                prmtop1.createSystem(nonbondedMethod=PME,
                    nonbondedCutoff=1*nanometer, switchDistance=1.2)
        )

    def test_with_dcd_reporter(self):
        """Check that an amber simulation like the docs example works with a DCD reporter."""

        temperature = 50*kelvin

        prmtop = prmtop4  # Mg + water
        inpcrd = inpcrd4  # Mg + water
        system = prmtop.createSystem(nonbondedMethod=PME, nonbondedCutoff=1*nanometer, constraints=HBonds)
        system.addForce(MonteCarloBarostat(1.0 * atmospheres, temperature, 1))

        integrator = LangevinIntegrator(temperature, 1.0 / picosecond, 0.0001 * picoseconds)

        simulation = Simulation(prmtop.topology, system, integrator)
        simulation.context.setPositions(inpcrd.positions)

        fname = tempfile.mktemp(suffix='.dcd')
        simulation.reporters.append(DCDReporter(fname, 1))  # This is an explicit test for the bugs in issue #850
        simulation.step(5)
        del simulation
        os.remove(fname)

    def testChamber(self):
        """Test a prmtop file created with Chamber."""
        prmtop = AmberPrmtopFile('systems/ala3_solv.parm7')
        crd = CharmmCrdFile('systems/ala3_solv.crd')
        system = prmtop.createSystem()
        for i,f in enumerate(system.getForces()):
            f.setForceGroup(i)
        integrator = VerletIntegrator(0.001)
        context = Context(system, integrator, Platform.getPlatform('Reference'))
        context.setPositions(crd.positions)
        
        # Compare to energies computed with pytraj.energy_decomposition()
        
        energy = context.getState(getEnergy=True).getPotentialEnergy().value_in_unit(kilocalories_per_mole)
        self.assertAlmostEqual(energy, -7806.981602, delta=5e-4*abs(energy))
        components = {}
        for i,f in enumerate(system.getForces()):
            components[f.getName()] = context.getState(getEnergy=True, groups={i}).getPotentialEnergy().value_in_unit(kilocalories_per_mole)
        self.assertAlmostEqual(components['HarmonicBondForce'], 1.13242125)
        self.assertAlmostEqual(components['HarmonicAngleForce'], 1.06880188)
        self.assertAlmostEqual(components['UreyBradleyForce'], 0.06142407)
        self.assertAlmostEqual(components['PeriodicTorsionForce'], 7.81143025)
        self.assertAlmostEqual(components['ImproperTorsionForce'], 2.66453526e-14, delta=1e-6)
        self.assertAlmostEqual(components['CMAPTorsionForce'], 0.12679003)
        self.assertAlmostEqual(components['CustomNonbondedForce'], 909.28136359)
        self.assertAlmostEqual(components['NonbondedForce'], -9007.16903192+277.35152722+3.35367163, delta=5e-4*abs(components['NonbondedForce']))

    def testGBneckRadii(self):
        """ Tests that GBneck radii limits are correctly enforced """
        from openmm.app.internal.customgbforces import GBSAGBnForce
        f = GBSAGBnForce()
        # Make sure legal parameters do not raise
        f.addParticle([0, 0.1, 0.5])
        f.addParticle([0, 0.2, 0.5])
        f.addParticle([0, 0.15, 0.5])
        # Now make sure that out-of-range parameters *do* raise
        self.assertRaises(ValueError, lambda: f.addParticle([0, 0.9, 0.5]))
        self.assertRaises(ValueError, lambda: f.addParticle([0, 0.21, 0.5]))

    def testNucleicGBParametes(self):
        """Test that correct GB parameters are used for nucleic acids."""
        prmtop = AmberPrmtopFile('systems/DNA_mbondi3.prmtop')
        inpcrd = AmberInpcrdFile('systems/DNA_mbondi3.inpcrd')
        sanderEnergy = [-19223.87993545, -19527.40433175, -19788.1070698]
        for solvent, expectedEnergy in zip([OBC2, GBn, GBn2], sanderEnergy):
            system = prmtop.createSystem(implicitSolvent=solvent, gbsaModel=None)
            for f in system.getForces():
                if isinstance(f, CustomGBForce) or isinstance(f, GBSAOBCForce):
                    f.setForceGroup(1)
            integrator = VerletIntegrator(0.001)
            context = Context(system, integrator, Platform.getPlatform('Reference'))
            context.setPositions(inpcrd.positions)
            energy = context.getState(getEnergy=True, groups={1}).getPotentialEnergy().value_in_unit(kilojoules_per_mole)
            self.assertAlmostEqual(energy, expectedEnergy, delta=5e-4*abs(energy))

    def testAmberCMAP(self):
        """Check that CMAP energy calcultion compared to AMber."""
        temperature = 50*kelvin
        conversion = 4.184 # 4.184 kJ/mol
        sander_CMAP_E = 8.2864 # CMAP energy calcluated by Amber, unit kcal/mol

        prmtop = prmtop7  # systems/18protein.parm7
        inpcrd = inpcrd7  # systems/18protein.rst7

        system = prmtop.createSystem(nonbondedMethod=PME, nonbondedCutoff=1.2)
        integrator = LangevinIntegrator(temperature, 1.0 / picosecond, 0.002 * picoseconds)

        simulation = Simulation(prmtop.topology, system, integrator)
        simulation.context.setPositions(inpcrd.positions)

        for i, force in enumerate(system.getForces()):
            force.setForceGroup(i)
            
        simulation.context.reinitialize(True)

        for i in range(system.getNumForces()):
            if i == 3: # 3 indicates CMAP force
#                print(simulation.context.getState(getEnergy=True, groups=1<<i).getPotentialEnergy().value_in_unit(kilojoules_per_mole))
                OpenMM_CMAP_E = simulation.context.getState(getEnergy=True, groups=1<<i).getPotentialEnergy().value_in_unit(kilojoules_per_mole)/conversion
                self.assertAlmostEqual(OpenMM_CMAP_E, sander_CMAP_E, places=4)

    def testEPConstraints(self):
        """Test different types of constraints when using extra particles"""
        prmtop = AmberPrmtopFile('systems/peptide_with_tip4p.prmtop')
        for constraints in (HBonds, AllBonds):
            system = prmtop.createSystem(constraints=constraints)
            integrator = VerletIntegrator(0.001*picoseconds)
            # If a constraint was added to a massless particle, this will throw an exception.
            context = Context(system, integrator, Platform.getPlatform('Reference'))

    def testWaterBonds(self):
        """Test that water molecules have the right set of bonds"""
        top = prmtop1.topology
        for residue in top.residues():
            if residue.name == 'HOH':
                bonds = list(residue.bonds())
                self.assertEqual(2, len(bonds))
                for a1, a2 in bonds:
                    self.assertTrue(a1.element == elem.oxygen or a2.element == elem.oxygen)
                    self.assertTrue(a1.element == elem.hydrogen or a2.element == elem.hydrogen)

    def testFlexibleConstraints(self):
        """Test the flexibleConstraints option"""
        energies = {}
        forces = {}
        for flexibleConstraints in [False, True]:
            system = prmtop1.createSystem(nonbondedMethod=PME, constraints=HAngles, flexibleConstraints=flexibleConstraints)
            for i, f in enumerate(system.getForces()):
                f.setForceGroup(i)
            integrator = VerletIntegrator(1.0*femtoseconds)
            sim = Simulation(prmtop1.topology, system, integrator, Platform.getPlatform('Reference'))
            sim.context.setPositions(inpcrd1.positions)
            energies[flexibleConstraints] = {}
            for i, f in enumerate(system.getForces()):
                forces[i] = f
                energies[flexibleConstraints][i] = sim.context.getState(getEnergy=True, groups={i}).getPotentialEnergy().value_in_unit(kilojoules_per_mole)
        for i, f in forces.items():
            delta = 1e-5*abs(energies[True][i])
            if isinstance(f, HarmonicBondForce) or isinstance(f, HarmonicAngleForce):
                self.assertNotAlmostEqual(energies[True][i], energies[False][i], delta=delta)
            else:
                self.assertAlmostEqual(energies[True][i], energies[False][i], delta=delta)

if __name__ == '__main__':
    unittest.main()
