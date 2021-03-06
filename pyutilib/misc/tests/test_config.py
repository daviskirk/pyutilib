#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

import sys
import os
import os.path
import pickle
import re

currdir = os.path.dirname(os.path.abspath(__file__))
import pyutilib.th as unittest

import pyutilib.misc.comparison
from pyutilib.misc.config import ConfigValue, ConfigBlock, ConfigList

from six import PY3, StringIO

try:
    import yaml
    using_yaml = True
except ImportError:
    using_yaml = False

# Utility to redirect display() to a string
def _display(obj, *args):
    test = StringIO()
    obj.display(ostream=test, *args)
    return test.getvalue()

class Test(unittest.TestCase):

    def setUp(self):
        self.config = config = ConfigBlock(
            "Basic configuration for Flushing models", implicit=True)
        net = config.declare('network', ConfigBlock())
        net.declare('epanet file',
                    ConfigValue('Net3.inp', str, 'EPANET network inp file',
                                None)).declare_as_argument(dest='epanet')

        sc = config.declare(
            'scenario',
            ConfigBlock(
                "Single scenario block", implicit=True, implicit_domain=str))
        sc.declare('scenario file', ConfigValue(
            'Net3.tsg', str,
            'Scenario generation file, see the TEVASIM documentation',
            """This is the (long) documentation for the 'scenario file'
            parameter.  It contains multiple lines, and some internal
            formatting; like a bulleted list:
              - item 1
              - item 2
            """)).declare_as_argument(group='Scenario definition')
        sc.declare('merlion', ConfigValue(
            False, bool, 'Water quality model',
            """This is the (long) documentation for the 'merlion'
parameter.  It contains multiple lines, but no apparent internal
formatting; so the outputter should re-wrap everything.
""")).declare_as_argument(group='Scenario definition')
        sc.declare('detection',
                   ConfigValue(
                       # Note use of lambda for an "integer list domain"
                       [1, 2, 3],
                       lambda x: list(int(i) for i in x),
                       'Sensor placement list, epanetID',
                       None))

        config.declare('scenarios', ConfigList([], sc,
                                               "List of scenario blocks", None))

        config.declare('nodes', ConfigList(
            [], ConfigValue(0, int, 'Node ID', None), "List of node IDs", None))

        im = config.declare('impact', ConfigBlock())
        im.declare('metric', ConfigValue(
            'MC', str, 'Population or network based impact metric', None))

        fl = config.declare('flushing', ConfigBlock())
        n = fl.declare('flush nodes', ConfigBlock())
        n.declare('feasible nodes', ConfigValue(
            'ALL', str, 'ALL, NZD, NONE, list or filename', None))
        n.declare('infeasible nodes', ConfigValue(
            'NONE', str, 'ALL, NZD, NONE, list or filename', None))
        n.declare('max nodes',
                  ConfigValue(2, int, 'Maximum number of nodes to flush', None))
        n.declare('rate', ConfigValue(600, float, 'Flushing rate [gallons/min]',
                                      None))
        n.declare('response time', ConfigValue(
            60, float, 'Time [min] between detection and flushing', None))
        n.declare('duration', ConfigValue(600, float, 'Time [min] for flushing',
                                          None))

        v = fl.declare('close valves', ConfigBlock())
        v.declare('feasible pipes', ConfigValue(
            'ALL', str, 'ALL, DIAM min max [inch], NONE, list or filename',
            None))
        v.declare('infeasible pipes', ConfigValue(
            'NONE', str, 'ALL, DIAM min max [inch], NONE, list or filename',
            None))
        v.declare('max pipes',
                  ConfigValue(2, int, 'Maximum number of pipes to close', None))
        v.declare('response time', ConfigValue(
            60, float, 'Time [min] between detection and closing valves', None))

        self._reference = {
            'network': {
                'epanet file': 'Net3.inp'
            },
            'scenario': {
                'detection': [1, 2, 3],
                'scenario file': 'Net3.tsg',
                'merlion': False
            },
            'scenarios': [],
            'nodes': [],
            'impact': {
                'metric': 'MC'
            },
            'flushing': {
                'close valves': {
                    'infeasible pipes': 'NONE',
                    'max pipes': 2,
                    'feasible pipes': 'ALL',
                    'response time': 60.0
                },
                'flush nodes': {
                    'feasible nodes': 'ALL',
                    'max nodes': 2,
                    'infeasible nodes': 'NONE',
                    'rate': 600.0,
                    'duration': 600.0,
                    'response time': 60.0
                },
            },
        }

    # Utility method for generating and validating a template description
    def _validateTemplate(self, reference_template, **kwds):
        test = self.config.generate_yaml_template(**kwds)
        width = kwds.get('width', 80)
        indent = kwds.get('indent_spacing', 2)
        sys.stdout.write(test)
        for l in test.splitlines():
            self.assertLessEqual(len(l), width)
            if l.strip().startswith("#"):
                continue
            self.assertEqual((len(l) - len(l.lstrip())) % indent, 0)
        self.assertEqual(test, reference_template)

    def test_template_default(self):
        reference_template = """# Basic configuration for Flushing models
network:
  epanet file: Net3.inp     # EPANET network inp file
scenario:                   # Single scenario block
  scenario file: Net3.tsg   # Scenario generation file, see the TEVASIM
                            #   documentation
  merlion: false            # Water quality model
  detection: [1, 2, 3]      # Sensor placement list, epanetID
scenarios: []               # List of scenario blocks
nodes: []                   # List of node IDs
impact:
  metric: MC                # Population or network based impact metric
flushing:
  flush nodes:
    feasible nodes: ALL     # ALL, NZD, NONE, list or filename
    infeasible nodes: NONE  # ALL, NZD, NONE, list or filename
    max nodes: 2            # Maximum number of nodes to flush
    rate: 600.0             # Flushing rate [gallons/min]
    response time: 60.0     # Time [min] between detection and flushing
    duration: 600.0         # Time [min] for flushing
  close valves:
    feasible pipes: ALL     # ALL, DIAM min max [inch], NONE, list or filename
    infeasible pipes: NONE  # ALL, DIAM min max [inch], NONE, list or filename
    max pipes: 2            # Maximum number of pipes to close
    response time: 60.0     # Time [min] between detection and closing valves
"""
        self._validateTemplate(reference_template)

    def test_template_3space(self):
        reference_template = """# Basic configuration for Flushing models
network:
   epanet file: Net3.inp      # EPANET network inp file
scenario:                     # Single scenario block
   scenario file: Net3.tsg    # Scenario generation file, see the TEVASIM
                              #   documentation
   merlion: false             # Water quality model
   detection: [1, 2, 3]       # Sensor placement list, epanetID
scenarios: []                 # List of scenario blocks
nodes: []                     # List of node IDs
impact:
   metric: MC                 # Population or network based impact metric
flushing:
   flush nodes:
      feasible nodes: ALL     # ALL, NZD, NONE, list or filename
      infeasible nodes: NONE  # ALL, NZD, NONE, list or filename
      max nodes: 2            # Maximum number of nodes to flush
      rate: 600.0             # Flushing rate [gallons/min]
      response time: 60.0     # Time [min] between detection and flushing
      duration: 600.0         # Time [min] for flushing
   close valves:
      feasible pipes: ALL     # ALL, DIAM min max [inch], NONE, list or
                              #   filename
      infeasible pipes: NONE  # ALL, DIAM min max [inch], NONE, list or
                              #   filename
      max pipes: 2            # Maximum number of pipes to close
      response time: 60.0     # Time [min] between detection and closing
                              #   valves
"""
        self._validateTemplate(reference_template, indent_spacing=3)

    def test_template_4space(self):
        reference_template = """# Basic configuration for Flushing models
network:
    epanet file: Net3.inp       # EPANET network inp file
scenario:                       # Single scenario block
    scenario file: Net3.tsg     # Scenario generation file, see the TEVASIM
                                #   documentation
    merlion: false              # Water quality model
    detection: [1, 2, 3]        # Sensor placement list, epanetID
scenarios: []                   # List of scenario blocks
nodes: []                       # List of node IDs
impact:
    metric: MC                  # Population or network based impact metric
flushing:
    flush nodes:
        feasible nodes: ALL     # ALL, NZD, NONE, list or filename
        infeasible nodes: NONE  # ALL, NZD, NONE, list or filename
        max nodes: 2            # Maximum number of nodes to flush
        rate: 600.0             # Flushing rate [gallons/min]
        response time: 60.0     # Time [min] between detection and flushing
        duration: 600.0         # Time [min] for flushing
    close valves:
        feasible pipes: ALL     # ALL, DIAM min max [inch], NONE, list or
                                #   filename
        infeasible pipes: NONE  # ALL, DIAM min max [inch], NONE, list or
                                #   filename
        max pipes: 2            # Maximum number of pipes to close
        response time: 60.0     # Time [min] between detection and closing
                                #   valves
"""
        self._validateTemplate(reference_template, indent_spacing=4)

    def test_template_3space_narrow(self):
        reference_template = """# Basic configuration for Flushing models
network:
   epanet file: Net3.inp    # EPANET network inp file
scenario:                   # Single scenario block
   scenario file: Net3.tsg  # Scenario generation file, see the TEVASIM
                            #   documentation
   merlion: false           # Water quality model
   detection: [1, 2, 3]     # Sensor placement list, epanetID
scenarios: []               # List of scenario blocks
nodes: []                   # List of node IDs
impact:
   metric: MC               # Population or network based impact metric
flushing:
   flush nodes:
      feasible nodes: ALL     # ALL, NZD, NONE, list or filename
      infeasible nodes: NONE  # ALL, NZD, NONE, list or filename
      max nodes: 2            # Maximum number of nodes to flush
      rate: 600.0             # Flushing rate [gallons/min]
      response time: 60.0     # Time [min] between detection and
                              #   flushing
      duration: 600.0         # Time [min] for flushing
   close valves:
      feasible pipes: ALL     # ALL, DIAM min max [inch], NONE, list or
                              #   filename
      infeasible pipes: NONE  # ALL, DIAM min max [inch], NONE, list or
                              #   filename
      max pipes: 2            # Maximum number of pipes to close
      response time: 60.0     # Time [min] between detection and closing
                              #   valves
"""
        self._validateTemplate(reference_template, indent_spacing=3, width=72)

    def test_display_default(self):
        reference = """network:
  epanet file: Net3.inp
scenario:
  scenario file: Net3.tsg
  merlion: false
  detection: [1, 2, 3]
scenarios: []
nodes: []
impact:
  metric: MC
flushing:
  flush nodes:
    feasible nodes: ALL
    infeasible nodes: NONE
    max nodes: 2
    rate: 600.0
    response time: 60.0
    duration: 600.0
  close valves:
    feasible pipes: ALL
    infeasible pipes: NONE
    max pipes: 2
    response time: 60.0
"""
        test = _display(self.config)
        sys.stdout.write(test)
        self.assertEqual(test, reference)

    def test_display_list(self):
        reference = """network:
  epanet file: Net3.inp
scenario:
  scenario file: Net3.tsg
  merlion: false
  detection: [1, 2, 3]
scenarios:
  -
    scenario file: Net3.tsg
    merlion: false
    detection: [1, 2, 3]
  -
    scenario file: Net3.tsg
    merlion: true
    detection: []
nodes: []
impact:
  metric: MC
flushing:
  flush nodes:
    feasible nodes: ALL
    infeasible nodes: NONE
    max nodes: 2
    rate: 600.0
    response time: 60.0
    duration: 600.0
  close valves:
    feasible pipes: ALL
    infeasible pipes: NONE
    max pipes: 2
    response time: 60.0
"""
        self.config['scenarios'].append()
        self.config['scenarios'].append({'merlion': True, 'detection': []})
        test = _display(self.config)
        sys.stdout.write(test)
        self.assertEqual(test, reference)

    def test_display_userdata_default(self):
        test = _display(self.config, 'userdata')
        sys.stdout.write(test)
        self.assertEqual(test, "")

    def test_display_userdata_list(self):
        self.config['scenarios'].append()
        test = _display(self.config, 'userdata')
        sys.stdout.write(test)
        self.assertEqual(test, """scenarios:
  -
""")

    def test_display_userdata_list_nonDefault(self):
        self.config['scenarios'].append()
        self.config['scenarios'].append({'merlion': True, 'detection': []})
        test = _display(self.config, 'userdata')
        sys.stdout.write(test)
        self.assertEqual(test, """scenarios:
  -
  -
    merlion: true
    detection: []
""")

    def test_display_userdata_block(self):
        self.config.add("foo", ConfigValue(0, int, None, None))
        self.config.add("bar", ConfigBlock())
        test = _display(self.config, 'userdata')
        sys.stdout.write(test)
        self.assertEqual(test, "")

    def test_display_userdata_block_nonDefault(self):
        self.config.add("foo", ConfigValue(0, int, None, None))
        self.config.add("bar", ConfigBlock(implicit=True)) \
                   .add("baz", ConfigBlock())
        test = _display(self.config, 'userdata')
        sys.stdout.write(test)
        self.assertEqual(test, "bar:\n")

    def test_unusedUserValues_default(self):
        test = '\n'.join(x.name(True) for x in self.config.unused_user_values())
        sys.stdout.write(test)
        self.assertEqual(test, "")

    def test_unusedUserValues_scalar(self):
        self.config['scenario']['merlion'] = True
        test = '\n'.join(x.name(True) for x in self.config.unused_user_values())
        sys.stdout.write(test)
        self.assertEqual(test, "scenario.merlion")

    def test_unusedUserValues_list(self):
        self.config['scenarios'].append()
        test = '\n'.join(x.name(True) for x in self.config.unused_user_values())
        sys.stdout.write(test)
        self.assertEqual(test, """scenarios
scenarios[0]""")

    def test_unusedUserValues_list_nonDefault(self):
        self.config['scenarios'].append()
        self.config['scenarios'].append({'merlion': True, 'detection': []})
        test = '\n'.join(x.name(True) for x in self.config.unused_user_values())
        sys.stdout.write(test)
        self.assertEqual(test, """scenarios
scenarios[0]
scenarios[1]
scenarios[1].merlion
scenarios[1].detection""")

    def test_unusedUserValues_list_nonDefault_listAccessed(self):
        self.config['scenarios'].append()
        self.config['scenarios'].append({'merlion': True, 'detection': []})
        for x in self.config['scenarios']:
            pass
        test = '\n'.join(x.name(True) for x in self.config.unused_user_values())
        sys.stdout.write(test)
        self.assertEqual(test, """scenarios[0]
scenarios[1]
scenarios[1].merlion
scenarios[1].detection""")

    def test_unusedUserValues_list_nonDefault_itemAccessed(self):
        self.config['scenarios'].append()
        self.config['scenarios'].append({'merlion': True, 'detection': []})
        self.config['scenarios'][1]['merlion']
        test = '\n'.join(x.name(True) for x in self.config.unused_user_values())
        sys.stdout.write(test)
        self.assertEqual(test, """scenarios[0]
scenarios[1].detection""")

    def test_unusedUserValues_topBlock(self):
        self.config.add('foo', ConfigBlock())
        test = '\n'.join(x.name(True) for x in self.config.unused_user_values())
        sys.stdout.write(test)
        self.assertEqual(test, "")

    def test_unusedUserValues_subBlock(self):
        self.config['scenario'].add('foo', ConfigBlock())
        test = '\n'.join(x.name(True) for x in self.config.unused_user_values())
        sys.stdout.write(test)
        self.assertEqual(test, """scenario
scenario.foo""")

    def test_UserValues_default(self):
        test = '\n'.join(x.name(True) for x in self.config.user_values())
        sys.stdout.write(test)
        self.assertEqual(test, "")

    def test_UserValues_scalar(self):
        self.config['scenario']['merlion'] = True
        test = '\n'.join(x.name(True) for x in self.config.user_values())
        sys.stdout.write(test)
        self.assertEqual(test, "scenario.merlion")

    def test_UserValues_list(self):
        self.config['scenarios'].append()
        test = '\n'.join(x.name(True) for x in self.config.user_values())
        sys.stdout.write(test)
        self.assertEqual(test, """scenarios
scenarios[0]""")

    def test_UserValues_list_nonDefault(self):
        self.config['scenarios'].append()
        self.config['scenarios'].append({'merlion': True, 'detection': []})
        test = '\n'.join(x.name(True) for x in self.config.user_values())
        sys.stdout.write(test)
        self.assertEqual(test, """scenarios
scenarios[0]
scenarios[1]
scenarios[1].merlion
scenarios[1].detection""")

    def test_UserValues_list_nonDefault_listAccessed(self):
        self.config['scenarios'].append()
        self.config['scenarios'].append({'merlion': True, 'detection': []})
        for x in self.config['scenarios']:
            pass
        test = '\n'.join(x.name(True) for x in self.config.user_values())
        sys.stdout.write(test)
        self.assertEqual(test, """scenarios
scenarios[0]
scenarios[1]
scenarios[1].merlion
scenarios[1].detection""")

    def test_UserValues_list_nonDefault_itemAccessed(self):
        self.config['scenarios'].append()
        self.config['scenarios'].append({'merlion': True, 'detection': []})
        self.config['scenarios'][1]['merlion']
        test = '\n'.join(x.name(True) for x in self.config.user_values())
        sys.stdout.write(test)
        self.assertEqual(test, """scenarios
scenarios[0]
scenarios[1]
scenarios[1].merlion
scenarios[1].detection""")

    def test_UserValues_topBlock(self):
        self.config.add('foo', ConfigBlock())
        test = '\n'.join(x.name(True) for x in self.config.user_values())
        sys.stdout.write(test)
        self.assertEqual(test, "")

    def test_UserValues_subBlock(self):
        self.config['scenario'].add('foo', ConfigBlock())
        test = '\n'.join(x.name(True) for x in self.config.user_values())
        sys.stdout.write(test)
        self.assertEqual(test, """scenario
scenario.foo""")

    def test_parseDisplayAndValue_default(self):
        if not using_yaml:
            self.skipTest("Cannot execute test because PyYAML is not available")
        test = _display(self.config)
        sys.stdout.write(test)
        self.assertEqual(yaml.load(test), self.config.value())

    def test_parseDisplayAndValue_list(self):
        if not using_yaml:
            self.skipTest("Cannot execute test because PyYAML is not available")
        self.config['scenarios'].append()
        self.config['scenarios'].append({'merlion': True, 'detection': []})
        test = _display(self.config)
        sys.stdout.write(test)
        self.assertEqual(yaml.load(test), self.config.value())

    def test_parseDisplay_userdata_default(self):
        if not using_yaml:
            self.skipTest("Cannot execute test because PyYAML is not available")
        test = _display(self.config, 'userdata')
        sys.stdout.write(test)
        self.assertEqual(yaml.load(test), None)

    def test_parseDisplay_userdata_list(self):
        if not using_yaml:
            self.skipTest("Cannot execute test because PyYAML is not available")
        self.config['scenarios'].append()
        test = _display(self.config, 'userdata')
        sys.stdout.write(test)
        self.assertEqual(yaml.load(test), {'scenarios': [None]})

    def test_parseDisplay_userdata_list_nonDefault(self):
        if not using_yaml:
            self.skipTest("Cannot execute test because PyYAML is not available")
        self.config['scenarios'].append()
        self.config['scenarios'].append({'merlion': True, 'detection': []})
        test = _display(self.config,'userdata')
        sys.stdout.write(test)
        self.assertEqual(
            yaml.load(test), {'scenarios':
                              [None, {'merlion': True,
                                      'detection': []}]})

    def test_parseDisplay_userdata_block(self):
        if not using_yaml:
            self.skipTest("Cannot execute test because PyYAML is not available")
        self.config.add("foo", ConfigValue(0, int, None, None))
        self.config.add("bar", ConfigBlock())
        test = _display(self.config, 'userdata')
        sys.stdout.write(test)
        self.assertEqual(yaml.load(test), None)

    def test_parseDisplay_userdata_block_nonDefault(self):
        if not using_yaml:
            self.skipTest("Cannot execute test because PyYAML is not available")
        self.config.add("foo", ConfigValue(0, int, None, None))
        self.config.add("bar", ConfigBlock(implicit=True)) \
                   .add("baz", ConfigBlock())
        test = _display(self.config, 'userdata')
        sys.stdout.write(test)
        self.assertEqual(yaml.load(test), {'bar': None})

    def test_value_ConfigValue(self):
        val = self.config['flushing']['flush nodes']['rate']
        self.assertIs(type(val), float)
        self.assertEqual(val, 600.0)

    def test_value_ConfigList_empty(self):
        val = self.config['nodes'].value()
        self.assertIs(type(val), list)
        self.assertEqual(val, [])

    def test_value_ConfigList_simplePopulated(self):
        self.config['nodes'].append('1')
        self.config['nodes'].append(3)
        self.config['nodes'].append()
        val = self.config['nodes'].value()
        self.assertIs(type(val), list)
        self.assertEqual(len(val), 3)
        self.assertEqual(val, [1, 3, 0])

    def test_value_ConfigList_complexPopulated(self):
        self.config['scenarios'].append()
        val = self.config['scenarios'].value()
        self.assertIs(type(val), list)
        self.assertEqual(len(val), 1)
        self.assertEqual(val, [{'detection': [1, 2, 3],
                                'merlion': False,
                                'scenario file': 'Net3.tsg'}])

    def test_name(self):
        self.config['scenarios'].append()
        self.assertEqual(self.config.name(), "")
        self.assertEqual(self.config['scenarios'].name(), "scenarios")
        self.assertEqual(self.config['scenarios'][0].name(), "[0]")
        self.assertEqual(self.config['scenarios'][0].get('merlion').name(),
                         "merlion")

    def test_name_fullyQualified(self):
        self.config['scenarios'].append()
        self.assertEqual(self.config.name(True), "")
        self.assertEqual(self.config['scenarios'].name(True), "scenarios")
        self.assertEqual(self.config['scenarios'][0].name(True), "scenarios[0]")
        self.assertEqual(self.config['scenarios'][0].get('merlion').name(True),
                         "scenarios[0].merlion")

    def test_setValue_scalar(self):
        self.config['flushing']['flush nodes']['rate'] = 50
        val = self.config['flushing']['flush nodes']['rate']
        self.assertIs(type(val), float)
        self.assertEqual(val, 50.0)

    def test_setValue_scalar_badDomain(self):
        try:
            self.config['flushing']['flush nodes']['rate'] = 'a'
        except ValueError:
            pass
        except:
            raise
        else:
            self.fail('expected test to raise ValueError')
        val = self.config['flushing']['flush nodes']['rate']
        self.assertIs(type(val), float)
        self.assertEqual(val, 600.0)

    def test_setValue_scalarList_empty(self):
        self.config['scenario']['detection'] = []
        val = self.config['scenario']['detection']
        self.assertIs(type(val), list)
        self.assertEqual(val, [])

    def test_setValue_scalarList_withvalue(self):
        self.config['scenario']['detection'] = [6]
        val = self.config['scenario']['detection']
        self.assertIs(type(val), list)
        self.assertEqual(val, [6])

    def test_setValue_scalarList_badDomain(self):
        try:
            self.config['scenario']['detection'] = 50
        except ValueError:
            pass
        except:
            raise
        else:
            self.fail('expected test to raise ValueError')
        val = self.config['scenario']['detection']
        self.assertIs(type(val), list)
        self.assertEqual(val, [1, 2, 3])

    def test_setValue_scalarList_badSubDomain(self):
        try:
            self.config['scenario']['detection'] = [5.5, 'a']
        except ValueError:
            pass
        except:
            raise
        else:
            self.fail('expected test to raise ValueError')
        val = self.config['scenario']['detection']
        self.assertIs(type(val), list)
        self.assertEqual(val, [1, 2, 3])

    def test_setValue_list_scalardomain_list(self):
        self.config['nodes'] = [5, 10]
        val = self.config['nodes'].value()
        self.assertIs(type(val), list)
        self.assertEqual(val, [5, 10])

    def test_setValue_list_scalardomain_scalar(self):
        self.config['nodes'] = 10
        val = self.config['nodes'].value()
        self.assertIs(type(val), list)
        self.assertEqual(val, [10])

    def test_setValue_list_badSubDomain(self):
        try:
            self.config['nodes'] = [5, 'a']
        except ValueError:
            pass
        except:
            raise
        else:
            self.fail('expected test to raise ValueError')
        val = self.config['nodes'].value()
        self.assertIs(type(val), list)
        self.assertEqual(val, [])

    def test_setValue_block_none(self):
        ref = self._reference['scenario']
        self.config['scenario'] = None
        self.assertEqual(ref, self.config['scenario'].value())
        self.config['scenario']['merlion'] = True
        ref['merlion'] = True
        self.assertEqual(ref, self.config['scenario'].value())
        self.config['scenario'] = None
        self.assertEqual(ref, self.config['scenario'].value())

    def test_setValue_block_empty(self):
        ref = self._reference['scenario']
        self.config['scenario'] = {}
        self.assertEqual(ref, self.config['scenario'].value())
        self.config['scenario']['merlion'] = True
        ref['merlion'] = True
        self.assertEqual(ref, self.config['scenario'].value())
        self.config['scenario'] = {}
        self.assertEqual(ref, self.config['scenario'].value())

    def test_setValue_block_simplevalue(self):
        _test = {'merlion': True, 'detection': [1]}
        ref = self._reference['scenario']
        ref.update(_test)
        self.config['scenario'] = _test
        self.assertEqual(ref, self.config['scenario'].value())

    def test_setItem_block_implicit(self):
        ref = self._reference
        ref['foo'] = 1
        self.config['foo'] = 1
        self.assertEqual(ref, self.config.value())
        ref['bar'] = 1
        self.config['bar'] = 1
        self.assertEqual(ref, self.config.value())

    def test_setItem_block_implicit_domain(self):
        ref = self._reference['scenario']
        ref['foo'] = '1'
        self.config['scenario']['foo'] = 1
        self.assertEqual(ref, self.config['scenario'].value())
        ref['bar'] = '1'
        self.config['scenario']['bar'] = 1
        self.assertEqual(ref, self.config['scenario'].value())

    def test_setValue_block_noImplicit(self):
        _test = {'epanet file': 'no_file.inp', 'foo': 1}
        try:
            self.config['network'] = _test
        except ValueError:
            pass
        except:
            raise
        else:
            self.fail("Expected test to raise ValueError")
        self.assertEqual(self._reference, self.config.value())

    def test_setValue_block_implicit(self):
        _test = {'scenario': {'merlion': True, 'detection': [1]}, 'foo': 1}
        ref = self._reference
        ref['scenario'].update(_test['scenario'])
        ref['foo'] = 1
        self.config.set_value(_test)
        self.assertEqual(ref, self.config.value())
        _test = {'scenario': {'merlion': True, 'detection': [1]}, 'bar': 1}
        ref['bar'] = 1
        self.config.set_value(_test)
        self.assertEqual(ref, self.config.value())

    def test_setValue_block_implicit_domain(self):
        _test = {'merlion': True, 'detection': [1], 'foo': 1}
        ref = self._reference['scenario']
        ref.update(_test)
        ref['foo'] = '1'
        self.config['scenario'] = _test
        self.assertEqual(ref, self.config['scenario'].value())
        _test = {'merlion': True, 'detection': [1], 'bar': '1'}
        ref['bar'] = '1'
        self.config['scenario'] = _test
        self.assertEqual(ref, self.config['scenario'].value())

    def test_setValue_block_badDomain(self):
        _test = {'merlion': True, 'detection': ['a'], 'foo': 1, 'a': 1}
        try:
            self.config['scenario'] = _test
        except ValueError:
            pass
        except:
            raise
        else:
            self.fail('expected test to raise ValueError')
        self.assertEqual(self._reference, self.config.value())

        try:
            self.config['scenario'] = []
        except ValueError:
            pass
        except:
            raise
        else:
            self.fail('expected test to raise ValueError')
        self.assertEqual(self._reference, self.config.value())

    def test_default_function(self):
        c = ConfigValue(default=lambda: 10, domain=int)
        self.assertEqual(c.value(), 10)
        c.set_value(5)
        self.assertEqual(c.value(), 5)
        c.reset()
        self.assertEqual(c.value(), 10)

        try:
            c = ConfigValue(default=lambda x: 10 * x, domain=int)
        except TypeError:
            pass
        else:
            self.fail("Expected type error")

        try:
            c = ConfigValue('a', domain=int)
        except ValueError:
            pass
        except:
            raise
        else:
            self.fail("Expected casting a to int to raise a value error")

    def test_getItem_setItem(self):
        # a freshly-initialized object should not be accessed
        self.assertFalse(self.config._userAccessed)
        self.assertFalse(self.config._data['scenario']._userAccessed)
        self.assertFalse(self.config._data['scenario']._data['detection']\
                             ._userAccessed)

        # Getting a ConfigValue should not access it
        self.assertFalse(self.config['scenario'].get('detection')._userAccessed)

        #... but should access the parent blocks traversed to get there
        self.assertTrue(self.config._userAccessed)
        self.assertTrue(self.config._data['scenario']._userAccessed)
        self.assertFalse(self.config._data['scenario']._data['detection']\
                             ._userAccessed)

        # a freshly-initialized object should not be set
        self.assertFalse(self.config._userSet)
        self.assertFalse(self.config._data['scenario']._userSet)
        self.assertFalse(self.config['scenario']._data['detection']._userSet)

        # setting a value should map it to the correct domain
        self.assertEqual(self.config['scenario']['detection'], [1, 2, 3])
        self.config['scenario']['detection'] = [42.5]
        self.assertEqual(self.config['scenario']['detection'], [42])

        # setting a ConfigValue should mark it as userSet, but NOT any parent blocks
        self.assertFalse(self.config._userSet)
        self.assertFalse(self.config._data['scenario']._userSet)
        self.assertTrue(self.config['scenario'].get('detection')._userSet)

    def test_generate_documentation(self):
        oFile = os.path.join(currdir, 'test_reference.out')
        OUTPUT = open(oFile, 'w')
        test = self.config.generate_documentation()
        OUTPUT.write(test)
        OUTPUT.close()
        print(test)
        self.assertFalse(
            pyutilib.misc.comparison.compare_file(oFile, oFile[:-4] + '.txt')[
                0])
        os.remove(oFile)

    def test_generate_custom_documentation(self):
        reference = \
"""startBlock{}
  startItem{network}
  endItem{network}
  startBlock{network}
    startItem{epanet file}
      item{EPANET network inp file}
    endItem{epanet file}
  endBlock{network}
  startItem{scenario}
    item{Single scenario block}
  endItem{scenario}
  startBlock{scenario}
    startItem{scenario file}
item{This is the (long) documentation for the 'scenario file'
parameter.  It contains multiple lines, and some internal
formatting; like a bulleted list:
  - item 1
  - item 2
}
    endItem{scenario file}
    startItem{merlion}
      item{This is the (long) documentation for the 'merlion' parameter.  It
      contains multiple lines, but no apparent internal formatting; so the
      outputter should re-wrap everything.}
    endItem{merlion}
    startItem{detection}
      item{Sensor placement list, epanetID}
    endItem{detection}
  endBlock{scenario}
  startItem{scenarios}
    item{List of scenario blocks}
  endItem{scenarios}
  startBlock{scenarios}
    startItem{scenario file}
item{This is the (long) documentation for the 'scenario file'
parameter.  It contains multiple lines, and some internal
formatting; like a bulleted list:
  - item 1
  - item 2
}
    endItem{scenario file}
    startItem{merlion}
      item{This is the (long) documentation for the 'merlion' parameter.  It
      contains multiple lines, but no apparent internal formatting; so the
      outputter should re-wrap everything.}
    endItem{merlion}
    startItem{detection}
      item{Sensor placement list, epanetID}
    endItem{detection}
  endBlock{scenarios}
  startItem{nodes}
    item{List of node IDs}
  endItem{nodes}
  startItem{impact}
  endItem{impact}
  startBlock{impact}
    startItem{metric}
      item{Population or network based impact metric}
    endItem{metric}
  endBlock{impact}
  startItem{flushing}
  endItem{flushing}
  startBlock{flushing}
    startItem{flush nodes}
    endItem{flush nodes}
    startBlock{flush nodes}
      startItem{feasible nodes}
        item{ALL, NZD, NONE, list or filename}
      endItem{feasible nodes}
      startItem{infeasible nodes}
        item{ALL, NZD, NONE, list or filename}
      endItem{infeasible nodes}
      startItem{max nodes}
        item{Maximum number of nodes to flush}
      endItem{max nodes}
      startItem{rate}
        item{Flushing rate [gallons/min]}
      endItem{rate}
      startItem{response time}
        item{Time [min] between detection and flushing}
      endItem{response time}
      startItem{duration}
        item{Time [min] for flushing}
      endItem{duration}
    endBlock{flush nodes}
    startItem{close valves}
    endItem{close valves}
    startBlock{close valves}
      startItem{feasible pipes}
        item{ALL, DIAM min max [inch], NONE, list or filename}
      endItem{feasible pipes}
      startItem{infeasible pipes}
        item{ALL, DIAM min max [inch], NONE, list or filename}
      endItem{infeasible pipes}
      startItem{max pipes}
        item{Maximum number of pipes to close}
      endItem{max pipes}
      startItem{response time}
        item{Time [min] between detection and closing valves}
      endItem{response time}
    endBlock{close valves}
  endBlock{flushing}
endBlock{}
"""
        test = self.config.generate_documentation(
            block_start= "startBlock{%s}\n",
            block_end=   "endBlock{%s}\n",
            item_start=  "startItem{%s}\n",
            item_body=   "item{%s}\n",
            item_end=    "endItem{%s}\n",
        )
        print(test)
        self.assertEqual(test, reference)

        test = self.config.generate_documentation(
            block_start= "startBlock\n",
            block_end=   "endBlock\n",
            item_start=  "startItem\n",
            item_body=   "item\n",
            item_end=    "endItem\n",
        )

        # re.sub(flags=) was introduced in 2.7
        if sys.version_info[:2] < (2,7):
            stripped_reference = re.sub('\{[^\}]*\}','',reference)
        else:
            stripped_reference = re.sub('\{[^\}]*\}','',reference,flags=re.M)
        print(test)
        self.assertEqual(test, stripped_reference)

    def test_block_get(self):
        self.assertTrue('scenario' in self.config)
        self.assertNotEquals(
            self.config.get('scenario', 'bogus').value(), 'bogus')
        self.assertFalse('fubar' in self.config)
        self.assertEquals(
            self.config.get('fubar', 'bogus').value(), 'bogus')

        cfg = ConfigBlock()
        cfg.declare('foo', ConfigValue(1, int))
        self.assertEqual( cfg.get('foo', 5).value(), 1 )
        self.assertEqual( len(cfg), 1 )
        self.assertIs( cfg.get('bar'), None )
        self.assertEqual( cfg.get('bar',None).value(), None )
        self.assertEqual( len(cfg), 1 )

        cfg = ConfigBlock(implicit=True)
        cfg.declare('foo', ConfigValue(1, int))
        self.assertEqual( cfg.get('foo', 5).value(), 1 )
        self.assertEqual( len(cfg), 1 )
        self.assertEqual( cfg.get('bar', 5).value(), 5 )
        self.assertEqual( len(cfg), 1 )
        self.assertIs( cfg.get('baz'), None )
        self.assertIs( cfg.get('baz', None).value(), None )
        self.assertEqual( len(cfg), 1 )

        cfg = ConfigBlock( implicit=True,
                           implicit_domain=ConfigList(domain=str) )
        cfg.declare('foo', ConfigValue(1, int))
        self.assertEqual( cfg.get('foo', 5).value(), 1 )
        self.assertEqual( len(cfg), 1 )
        self.assertEqual( cfg.get('bar', [5]).value(), ['5'] )
        self.assertEqual( len(cfg), 1 )
        self.assertIs( cfg.get('baz'), None )
        self.assertEqual( cfg.get('baz', None).value(), [] )
        self.assertEqual( len(cfg), 1 )

    def test_setdefault(self):
        cfg = ConfigBlock()
        cfg.declare('foo', ConfigValue(1, int))
        self.assertEqual( cfg.setdefault('foo', 5).value(), 1 )
        self.assertEqual( len(cfg), 1 )
        self.assertRaisesRegexp(ValueError, '.*disallows implicit entries',
                                cfg.setdefault, 'bar', 0)
        self.assertEqual( len(cfg), 1 )

        cfg = ConfigBlock(implicit=True)
        cfg.declare('foo', ConfigValue(1, int))
        self.assertEqual( cfg.setdefault('foo', 5).value(), 1 )
        self.assertEqual( len(cfg), 1 )
        self.assertEqual( cfg.setdefault('bar', 5).value(), 5 )
        self.assertEqual( len(cfg), 2 )
        self.assertEqual( cfg.setdefault('baz').value(), None )
        self.assertEqual( len(cfg), 3 )

        cfg = ConfigBlock( implicit=True,
                           implicit_domain=ConfigList(domain=str) )
        cfg.declare('foo', ConfigValue(1, int))
        self.assertEqual( cfg.setdefault('foo', 5).value(), 1 )
        self.assertEqual( len(cfg), 1 )
        self.assertEqual( cfg.setdefault('bar', [5]).value(), ['5'] )
        self.assertEqual( len(cfg), 2 )
        self.assertEqual( cfg.setdefault('baz').value(), [] )
        self.assertEqual( len(cfg), 3 )

    def test_block_keys(self):
        ref = ['scenario file', 'merlion', 'detection']

        # list of keys
        keys = self.config['scenario'].keys()
        # lists are independent
        self.assertFalse(keys is self.config['scenario'].keys())
        if PY3:
            self.assertIsNot(type(keys), list)
            self.assertEqual(list(keys), ref)
        else:
            self.assertIs(type(keys), list)
            self.assertEqual(keys, ref)

        # keys iterator
        keyiter = self.config['scenario'].iterkeys()
        self.assertIsNot(type(keyiter), list)
        self.assertEqual(list(keyiter), ref)
        # iterators are independent
        self.assertFalse(keyiter is self.config['scenario'].iterkeys())

        # default iterator
        keyiter = self.config['scenario'].__iter__()
        self.assertIsNot(type(keyiter), list)
        self.assertEqual(list(keyiter), ref)
        # iterators are independent
        self.assertFalse(keyiter is self.config['scenario'].__iter__())

    def test_block_values(self):
        ref = ['Net3.tsg', False, [1, 2, 3]]

        # list of values
        values = self.config['scenario'].values()
        if PY3:
            self.assertIsNot(type(values), list)
        else:
            self.assertIs(type(values), list)
        self.assertEqual(list(values), ref)
        # lists are independent
        self.assertFalse(values is self.config['scenario'].values())

        # values iterator
        valueiter = self.config['scenario'].itervalues()
        self.assertIsNot(type(valueiter), list)
        self.assertEqual(list(valueiter), ref)
        # iterators are independent
        self.assertFalse(valueiter is self.config['scenario'].itervalues())

    def test_block_items(self):
        ref = [('scenario file', 'Net3.tsg'), ('merlion', False),
               ('detection', [1, 2, 3])]

        # list of items
        items = self.config['scenario'].items()
        if PY3:
            self.assertIsNot(type(items), list)
        else:
            self.assertIs(type(items), list)
        self.assertEqual(list(items), ref)
        # lists are independent
        self.assertFalse(items is self.config['scenario'].items())

        # items iterator
        itemiter = self.config['scenario'].iteritems()
        self.assertIsNot(type(itemiter), list)
        self.assertEqual(list(itemiter), ref)
        # iterators are independent
        self.assertFalse(itemiter is self.config['scenario'].iteritems())

    def test_value(self):
        print(self.config.value())
        self.assertEqual(self._reference, self.config.value())

    def test_list_manipulation(self):
        self.assertEqual(len(self.config['scenarios']), 0)
        self.config['scenarios'].append()
        self.assertEqual(len(self.config['scenarios']), 1)
        self.config['scenarios'].append({'merlion': True, 'detection': []})
        self.assertEqual(len(self.config['scenarios']), 2)
        test = _display(self.config, 'userdata')
        sys.stdout.write(test)
        self.assertEqual(test, """scenarios:
  -
  -
    merlion: true
    detection: []
""")
        self.config['scenarios'][0] = {'merlion': True, 'detection': []}
        self.assertEqual(len(self.config['scenarios']), 2)
        test = _display(self.config, 'userdata')
        sys.stdout.write(test)
        self.assertEqual(test, """scenarios:
  -
    merlion: true
    detection: []
  -
    merlion: true
    detection: []
""")
        test = _display(self.config['scenarios'])
        sys.stdout.write(test)
        self.assertEqual(test, """-
  scenario file: Net3.tsg
  merlion: true
  detection: []
-
  scenario file: Net3.tsg
  merlion: true
  detection: []
""")

    def test_list_get(self):
        X = ConfigBlock(implicit=True)
        X.config = ConfigList()
        self.assertEqual(_display(X, 'userdata'), "")
        self.assertIs(X.config.get(0), None )
        self.assertIs(X.config.get(0,None).value(), None )
        self.assertRaisesRegexp(
            IndexError, '.*out of range', X.config.__getitem__, 0 )
        # get() shouldn't change the userdata flag...
        self.assertEqual(_display(X, 'userdata'), "")

        X = ConfigBlock(implicit=True)
        X.config = ConfigList([42], int)
        self.assertEqual(_display(X, 'userdata'), "")
        val = X.config.get(0)
        self.assertEqual(val.value(), 42)
        self.assertIs(type(val), ConfigValue)
        # get() shouldn't change the userdata flag...
        self.assertEqual(_display(X, 'userdata'), "")
        val = X.config[0]
        self.assertIs(type(val), int)
        self.assertEqual(val, 42)
        # get() shouldn't change the userdata flag...
        self.assertEqual(_display(X, 'userdata'), "")

        self.assertIs(X.config.get(1), None )
        self.assertRaisesRegexp(
            IndexError, '.*out of range', X.config.__getitem__, 1)

        # this should ONLY change the userSet flag on the item (and not
        # the list)
        X.config.get(0).set_value(20)
        self.assertEqual(_display(X, 'userdata'), "  - 20\n")

        # this should ONLY change the userSet flag on the item (and not
        # the list)
        X = ConfigBlock(implicit=True)
        X.config = ConfigList([42], int)
        X.config[0] = 20
        self.assertEqual(_display(X, 'userdata'), "  - 20\n")

        # This should change both...
        X = ConfigBlock(implicit=True)
        X.config = ConfigList([42], int)
        X.config.append(20)
        self.assertEqual(_display(X, 'userdata'), "config:\n  - 20\n")

    def test_implicit_entries(self):
        config = ConfigBlock()
        try:
            config['test'] = 5
            self.fail(
                "Expected ConfigBlock to throw a ValueError for implicit declarations")
        except ValueError:
            self.assertEqual(sys.exc_info()[1].args, (
                "Key 'test' not defined in Config Block '' and Block disallows implicit entries",
            ))

        config = ConfigBlock(implicit=True)
        config['implicit_1'] = 5
        config.declare('formal', ConfigValue(42, int))
        config['implicit_2'] = 5
        self.assertEqual(3, len(config))
        self.assertEqual(['implicit_1', 'formal', 'implicit_2'],
                         list(config.iterkeys()))
        config.reset()
        self.assertEqual(1, len(config))
        self.assertEqual(['formal'], list(config.iterkeys()))

    def test_argparse_help(self):
        try:
            import argparse
        except ImportError:
            self.skipTest("argparse not available")
        parser = argparse.ArgumentParser(prog='tester')
        self.config.initialize_argparse(parser)
        help = parser.format_help()
        print(help)
        self.assertEqual(
            """usage: tester [-h] [--epanet-file EPANET] [--scenario-file STR] [--merlion]

optional arguments:
  -h, --help            show this help message and exit
  --epanet-file EPANET  EPANET network inp file

Scenario definition:
  --scenario-file STR   Scenario generation file, see the TEVASIM
                        documentation
  --merlion             Water quality model
""", help)

    def test_argparse_help_implicit_disable(self):
        self.config['scenario'].declare('epanet', ConfigValue(
            True, bool, 'Use EPANET as the Water quality model',
            None)).declare_as_argument(group='Scenario definition')
        try:
            import argparse
        except ImportError:
            self.skipTest("argparse not available")
        parser = argparse.ArgumentParser(prog='tester')
        self.config.initialize_argparse(parser)
        help = parser.format_help()
        print(help)
        self.assertEqual(
            """usage: tester [-h] [--epanet-file EPANET] [--scenario-file STR] [--merlion]
              [--disable-epanet]

optional arguments:
  -h, --help            show this help message and exit
  --epanet-file EPANET  EPANET network inp file

Scenario definition:
  --scenario-file STR   Scenario generation file, see the TEVASIM
                        documentation
  --merlion             Water quality model
  --disable-epanet      [DON'T] Use EPANET as the Water quality model
""", help)

    def test_argparse_import(self):
        try:
            import argparse
        except ImportError:
            self.skipTest("argparse not available")
        parser = argparse.ArgumentParser(prog='tester')
        self.config.initialize_argparse(parser)

        args = parser.parse_args([])
        self.assertEqual(0, len(vars(args)))
        leftovers = self.config.import_argparse(args)
        self.assertEqual(0, len(vars(args)))
        self.assertEqual([], [x.name(True) for x in self.config.user_values()])

        args = parser.parse_args(['--merlion'])
        self.config.reset()
        self.assertFalse(self.config['scenario']['merlion'])
        self.assertEqual(1, len(vars(args)))
        leftovers = self.config.import_argparse(args)
        self.assertEqual(0, len(vars(args)))
        self.assertEqual(['scenario.merlion'],
                         [x.name(True) for x in self.config.user_values()])

        args = parser.parse_args(['--merlion', '--epanet-file', 'foo'])
        self.config.reset()
        self.assertFalse(self.config['scenario']['merlion'])
        self.assertEqual('Net3.inp', self.config['network']['epanet file'])
        self.assertEqual(2, len(vars(args)))
        leftovers = self.config.import_argparse(args)
        self.assertEqual(1, len(vars(args)))
        self.assertEqual(['network.epanet file', 'scenario.merlion'],
                         [x.name(True) for x in self.config.user_values()])
        self.assertTrue(self.config['scenario']['merlion'])
        self.assertEqual('foo', self.config['network']['epanet file'])

    def test_argparse_subparsers(self):
        try:
            import argparse
        except ImportError:
            self.skipTest("argparse not available")
        parser = argparse.ArgumentParser(prog='tester')
        subp = parser.add_subparsers(title="Subcommands").add_parser('flushing')

        # Declare an argument by passing in the name of the subparser
        self.config['flushing']['flush nodes'].get(
            'duration').declare_as_argument(group='flushing')
        # Declare an argument by passing in the name of the subparser
        # and an implicit group
        self.config['flushing']['flush nodes'].get('feasible nodes') \
            .declare_as_argument( group=('flushing','Node information') )
        # Declare an argument by passing in the subparser and a group name
        self.config['flushing']['flush nodes'].get('infeasible nodes') \
            .declare_as_argument( group=(subp,'Node information') )
        self.config.initialize_argparse(parser)

        help = parser.format_help()
        print(help)
        self.assertEqual(
            """usage: tester [-h] [--epanet-file EPANET] [--scenario-file STR] [--merlion]
              {flushing} ...

optional arguments:
  -h, --help            show this help message and exit
  --epanet-file EPANET  EPANET network inp file

Subcommands:
  {flushing}

Scenario definition:
  --scenario-file STR   Scenario generation file, see the TEVASIM
                        documentation
  --merlion             Water quality model
""", help)

        help = subp.format_help()
        print(help)
        self.assertEqual(
            """usage: tester flushing [-h] [--feasible-nodes STR] [--infeasible-nodes STR]
                       [--duration FLOAT]

optional arguments:
  -h, --help            show this help message and exit
  --duration FLOAT      Time [min] for flushing

Node information:
  --feasible-nodes STR  ALL, NZD, NONE, list or filename
  --infeasible-nodes STR
                        ALL, NZD, NONE, list or filename
""", help)

    def test_getattr_setattr(self):
        config = ConfigBlock()
        foo = config.declare(
            'foo', ConfigBlock(
                implicit=True, implicit_domain=int))
        foo.declare('explicit_bar', ConfigValue(0, int))

        self.assertEqual(1, len(foo))
        self.assertEqual(0, foo['explicit_bar'])
        self.assertEqual(0, foo.explicit_bar)
        foo.explicit_bar = 10
        self.assertEqual(1, len(foo))
        self.assertEqual(10, foo['explicit_bar'])
        self.assertEqual(10, foo.explicit_bar)

        foo.implicit_bar = 20
        self.assertEqual(2, len(foo))
        self.assertEqual(20, foo['implicit bar'])
        self.assertEqual(20, foo.implicit_bar)

        try:
            config.baz = 10
        except ValueError:
            pass
        except:
            raise
        else:
            self.fail(
                "Expected implicit assignment to explicit block to raise ValueError")

        try:
            a = config.baz
        except AttributeError:
            pass
        except:
            raise
        else:
            self.fail(
                "Expected implicit assignment to explicit block to raise ValueError")


    def test_nonString_keys(self):
        config = ConfigBlock(implicit=True)
        config.declare(5, ConfigValue(50, int))
        self.assertIn(5, config)
        self.assertIn('5', config)
        self.assertEqual(config[5], 50)
        self.assertEqual(config['5'], 50)
        self.assertEqual(config.get(5).value(), 50)
        self.assertEqual(config.get('5').value(), 50)

        config[5] = 500
        self.assertIn(5, config)
        self.assertIn('5', config)
        self.assertEqual(config[5], 500)
        self.assertEqual(config['5'], 500)
        self.assertEqual(config.get(5).value(), 500)
        self.assertEqual(config.get('5').value(), 500)

        config[1] = 10
        self.assertIn(1, config)
        self.assertIn('1', config)
        self.assertEqual(config[1], 10)
        self.assertEqual(config['1'], 10)
        self.assertEqual(config.get(1).value(), 10)
        self.assertEqual(config.get('1').value(), 10)

        self.assertEqual(_display(config), "5: 500\n1: 10\n")

        config.set_value({5:5000})
        self.assertIn(1, config)
        self.assertIn('1', config)
        self.assertEqual(config[1], 10)
        self.assertEqual(config['1'], 10)
        self.assertEqual(config.get(1).value(), 10)
        self.assertEqual(config.get('1').value(), 10)
        self.assertIn(5, config)
        self.assertIn('5', config)
        self.assertEqual(config[5], 5000)
        self.assertEqual(config['5'], 5000)
        self.assertEqual(config.get(5).value(), 5000)
        self.assertEqual(config.get('5').value(), 5000)

    def test_pickle(self):
        # A simple test: pickle the default config and restore it.
        # calling other tests should still pass.
        pickle_str = pickle.dumps(self.config)
        self.config = None
        self.config = pickle.loads(pickle_str)
        self.test_display_list()


if __name__ == "__main__":
    unittest.main()
