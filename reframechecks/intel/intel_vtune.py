# Copyright 2019-2020 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# HPCTools Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys
import reframe as rfm
import reframe.utility.sanity as sn
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                '../common')))  # noqa: E402
import sphexa.sanity as sphs
import sphexa.sanity_intel as sphsintel
import sphexa.sanity_vtune as sphsvtune


@rfm.parameterized_test(*[[mpitask, steps]
                          # for mpitask in [24, 48, 96]
                          for mpitask in [48]
                          for steps in [1]
                          ])
class SphExaVtuneCheck(sphsvtune.VtuneBaseTest):
    # {{{
    '''
    This class runs the test code with Intel(R) VTune(TM) (mpi only):
    https://software.intel.com/en-us/vtune

    2 parameters can be set for simulation:

    :arg mpitask: number of mpi tasks; the size of the cube in the 3D
         square patch test is set with a dictionary depending on mpitask,
         but cubesize could also be on the list of parameters,
    :arg steps: number of simulation steps.
    '''
    # }}}

    def __init__(self, mpitask, steps):
        super().__init__()
        # {{{ pe
        self.descr = 'Tool validation'
        self.valid_prog_environs = ['PrgEnv-gnu', 'PrgEnv-intel',
                                    'PrgEnv-cray', 'PrgEnv-cray_classic',
                                    'PrgEnv-pgi']
        # self.valid_systems = ['daint:gpu', 'dom:gpu']
        self.valid_systems = ['*']
        self.maintainers = ['JG']
        self.tags = {'sph', 'hpctools', 'cpu'}
# }}}

# {{{ compile
        self.testname = 'sqpatch'
        self.modules = ['vtune_profiler/2020']
        self.prebuild_cmds = ['module rm xalt']
        self.prgenv_flags = {
            'PrgEnv-gnu': ['-I.', '-I./include', '-std=c++14', '-g', '-O3',
                           '-DUSE_MPI', '-DNDEBUG'],
            'PrgEnv-intel': ['-I.', '-I./include', '-std=c++14', '-g', '-O3',
                             '-DUSE_MPI', '-DNDEBUG'],
            'PrgEnv-cray': ['-I.', '-I./include', '-std=c++17', '-g', '-Ofast',
                            '-DUSE_MPI', '-DNDEBUG'],
            'PrgEnv-cray_classic': ['-I.', '-I./include', '-hstd=c++14', '-g',
                                    '-O3', '-hnoomp', '-DUSE_MPI', '-DNDEBUG'],
            'PrgEnv-pgi': ['-I.', '-I./include', '-std=c++14', '-g', '-O3',
                           '-DUSE_MPI', '-DNDEBUG'],
        }
        self.build_system = 'SingleSource'
        self.build_system.cxx = 'CC'
        self.sourcepath = '%s.cpp' % self.testname
        self.tool = 'vtune'
        self.executable = self.tool
        self.target_executable = './%s.exe' % self.testname
# {{{ openmp:
# 'PrgEnv-intel': ['-qopenmp'],
# 'PrgEnv-gnu': ['-fopenmp'],
# 'PrgEnv-pgi': ['-mp'],
# 'PrgEnv-cray_classic': ['-homp'],
# 'PrgEnv-cray': ['-fopenmp'],
# # '-homp' if lang == 'F90' else '-fopenmp',
# }}}
# }}}

# {{{ run
        ompthread = 1
        # This dictionary sets cubesize = f(mpitask), for instance:
        # if mpitask == 24:
        #     cubesize = 100
        size_dict = {24: 100, 48: 125, 96: 157, 192: 198, 384: 250, 480: 269,
                     960: 340, 1920: 428, 3840: 539, 7680: 680, 15360: 857,
                     6: 62, 1: 34
                     }
        cubesize = size_dict[mpitask]
        self.name = 'sphexa_vtune_{}_{:03d}mpi_{:03d}omp_{}n_{}steps'.format(
            self.testname, mpitask, ompthread, cubesize, steps)
        self.num_tasks = mpitask
        self.num_tasks_per_node = 24  # 72
# {{{ ht:
        # self.num_tasks_per_node = mpitask if mpitask < 36 else 36   # noht
        # self.use_multithreading = False  # noht
        # self.num_tasks_per_core = 1      # noht

        # self.num_tasks_per_node = mpitask if mpitask < 72 else 72
        # self.use_multithreading = True # ht
        # self.num_tasks_per_core = 2    # ht
# }}}
        self.num_cpus_per_task = ompthread
        self.num_tasks_per_core = 2
        self.use_multithreading = True
        self.exclusive = True
        self.time_limit = '10m'
        self.variables = {
            'CRAYPE_LINK_TYPE': 'dynamic',
            'OMP_NUM_THREADS': str(self.num_cpus_per_task),
        }
        self.dir_rpt = 'rpt'
        collect = 'hotspots'
        self.tool_opts = '-trace-mpi -collect %s -r ./%s -data-limit=0' % \
            (collect, self.dir_rpt)  # example dir: rpt.nid00032
        self.executable_opts = [self.tool_opts, '%s' % self.target_executable,
                                '-n %s' % cubesize, '-s %s' % steps, '2>&1']
        self.version_rpt = 'version.rpt'
        self.which_rpt = 'which.rpt'
        self.summary_rpt = 'summary.rpt'
        self.srcfile_rpt = 'srcfile.rpt'
        self.prerun_cmds = [
            'module rm xalt',
            'mv %s %s' % (self.executable, self.target_executable),
            '%s --version &> %s' % (self.tool, self.version_rpt),
            'which %s &> %s' % (self.tool, self.which_rpt),
        ]
        column = ('"CPU Time:Self,CPU Time:Effective Time:Self,'
                  'CPU Time:Spin Time:Self,CPU Time:Overhead Time:Self"')
        self.postrun_cmds = [
            # summary rpt: TODO: for ...
            # '%s -R hotspots -r %s* -column="CPU Time:Self" &> %s' %
            # (self.tool, self.dir_rpt, self.summary_rpt),
            # csv report:
            'for vtdir in %s.nid* ;do %s -R hotspots -r $vtdir/*.vtune '
            '-group-by=function -format=csv -csv-delimiter=semicolon '
            '-column=%s &>$vtdir.csv ;done' %
            (self.dir_rpt, self.tool, column),
            # keep as reminder:
            # '%s cat /proc/sys/kernel/perf_event_paranoid &> %s' %
            # (run_cmd, self.paranoid_rpt),
            # 'cd %s ;ln -s nid*.000 e000 ;cd -' % self.dir_rpt,
            # '%s --report=survey --project-dir=%s &> %s' %
            # (self.tool, self.dir_rpt, self.summary_rpt),
            'cp *_job.out %s' % self.dir_rpt,
        ]
# }}}

# {{{ sanity
        # sanity
        self.sanity_patterns = sn.all([
            # check the job output:
            sn.assert_found(r'Total time for iteration\(0\)', self.stdout),
            # check the tool's version:
            sn.assert_true(sphsintel.vtune_version(self)),
            # check the summary report:
            sn.assert_found(r'vtune: Executing actions 100 % done',
                            self.stdout)
        ])
# }}}

# {{{ performance
        # {{{ internal timers
        # use linux date as timer:
        self.prerun_cmds += ['echo starttime=`date +%s`']
        self.postrun_cmds += ['echo stoptime=`date +%s`']
        # }}}

#        # {{{ perf_patterns:
#        basic_perf_patterns = sn.evaluate(sphs.basic_perf_patterns(self))
#        tool_perf_patterns = sn.evaluate(sphsintel.vtune_perf_patterns(self))
#        self.perf_patterns = {**basic_perf_patterns, **tool_perf_patterns}
#        # }}}
#
#        # {{{ reference:
#        self.reference = sn.evaluate(sphs.basic_reference_scoped_d(self))
#        self.reference = sn.evaluate(sphsintel.vtune_tool_reference(self))
# }}}
# }}}

    @rfm.run_before('compile')
    def setflags(self):
        self.build_system.cxxflags = \
            self.prgenv_flags[self.current_environ.name]

    # TODO:
    # def setup(self, partition, environ, **job_opts):
    #     super().setup(partition, environ, **job_opts)
    #     partitiontype = partition.fullname.split(':')[1]
    #     if partitiontype == 'gpu':
    #         self.job.options = ['--constraint="gpu&perf"']
    #     elif partitiontype == 'mc':
    #         self.job.options = ['--constraint="mc&perf"']
