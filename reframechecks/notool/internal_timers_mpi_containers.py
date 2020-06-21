# Copyright 2019-2020 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# HPCTools Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys
import reframe as rfm
import reframe.utility.sanity as sn
# from reframe.core.launchers import LauncherWrapper
from reframe.core.backends import getlauncher
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                '../common')))  # noqa: E402
import sphexa.sanity as sphs

size_dict = {24: 100, 48: 125, 96: 157, 192: 198, 384: 250, 480: 269,
             960: 340, 1920: 428, 3840: 539, 7680: 680, 15360: 857,
             6: 62, 3: 49, 1: 34}
# mpi_tasks = [1, 3]
# steps = [0]
mpi_tasks = [24, 48, 96, 192, 384]
steps = [4]
nativejob_stdout = 'rfm_native_job.out'
# {{{ class SphExaSingularityCheckBase:
class SphExaSingularityCheckBase(rfm.RegressionTest):
    # {{{
    '''
    2 parameters can be set for simulation:

    :arg mpi_task: number of mpi tasks; the size of the cube in the 3D
         square patch test is set with a dictionary depending on mpi_task,
         but cubesize could also be on the list of parameters,
    :arg step: number of simulation steps.

    Dependencies are:
        - compute: inputs (mpi_task, step) ---srun---> *job.out
        - postprocess logs: inputs (*job.out) ---x---> termgraph.in
        - plot data: inputs (termgraph.in) ---termgraph.py---> termgraph.rpt
    '''
    # }}} 

    def __init__(self, mpi_task, step, container_d):
        super().__init__()
        # {{{ pe
        self.descr = 'Tool validation'
        self.valid_prog_environs = ['builtin', 'PrgEnv-gnu', 'PrgEnv-intel',
                                    'PrgEnv-pgi', 'PrgEnv-cray']
        # self.sourcesdir = None
        # self.valid_systems = ['daint:gpu', 'dom:gpu']
        self.valid_systems = ['*']
        self.maintainers = ['JG']
        self.tags = {'sph', 'hpctools', 'cpu', 'container'}
# }}}

# {{{ compile
        self.testname = 'sqpatch'
        self.modules = [container_d['modulefiles']]
        self.build_system = 'SingleSource'
        # self.build_system.cxx = 'CC'
        self.sourcepath = '%s.cpp' % self.testname
        self.native_executable = './%s.exe' % self.testname
        # unload xalt to avoid _buffer_decode error and,
        # unload container to build native app:
        prebuild_cmds = [
            'module rm xalt', f"module rm {container_d['modulefiles']}",
            'module load cray-mpich'
        ]
        self.prebuild_cmds = prebuild_cmds
        self.postbuild_cmds = [f"mv {container_d['runtime']} {self.native_executable}"]
        self.prgenv_flags = {
            'PrgEnv-gnu': ['-I.', '-I./include', '-std=c++14', '-g', '-O2',
                           '-DUSE_MPI', '-DNDEBUG'],
            'PrgEnv-intel': ['-I.', '-I./include', '-std=c++14', '-g', '-O2',
                             '-DUSE_MPI', '-DNDEBUG'],
            'PrgEnv-cray': ['-I.', '-I./include', '-std=c++17', '-g', '-O2',
                            '-DUSE_MPI', '-DNDEBUG'],
            'PrgEnv-pgi': ['-I.', '-I./include', '-std=c++14', '-g', '-O2',
                           '-DUSE_MPI', '-DNDEBUG'],
        }
        # self.executable = self.native_executable
# }}}

#  {{{ run
        ompthread = 1
        # self.name = 'sphexa_mpiP_{}_{:03d}mpi_{:03d}omp_{}n_{}step'.format(
        # self.name = 'sphexa_singularity_{}_{:03d}mpi_{:03d}omp_{}step'.format(
        #     self.testname, mpi_task, ompthread, step)
        self.num_tasks = mpi_task
        self.num_tasks_per_node = 24
        self.num_tasks_per_core = 2
        self.use_multithreading = True
        self.num_cpus_per_task = ompthread
        self.exclusive = True
        self.time_limit = '10m'
        self.variables['OMP_NUM_THREADS'] = str(self.num_cpus_per_task)
        # ---------------------------------------------------------------------
        #Noooooo: container_platform_options = 'run'
        # --- hello:
        # self.target_executable = '/myapps/mpi/mpi_test.x'
        # container_platform_repo = '$SCRATCH/CONTAINERS/singularity'
        # container_platform_image = '%s/ubuntu18.04_gnu_mpich314_jg.sif' % container_platform_repo
        # container_platform_variables = 'LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/gcc/8.3.0/snos/lib64'
        # singularity/ubuntu18.04_gnu_mpich314_jg.sif
        container_platform_options = container_d['options']
        container_platform_projectdir = container_d['projectdir']
        container_platform_repo = container_d['scratch']
        # container_platform_image = '%s/ub1804_cuda102_mpich314_gnu8+sph.sif' % container_platform_repo
        container_platform_image = '%s/%s' % (container_platform_repo, container_d['image'])
        # container_platform_variables = 'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/gcc/8.3.0/snos/lib64 &&'
        container_platform_variables = container_d['variables']
        container_platform_executable = container_d['executable']
        # container_platform_mount = '-B"/x:/x"'
        executable_arguments = container_d['executable_opts']
        self.prerun_cmds = [
            'module rm xalt',
            # rsync -av /project/csstaff/piccinal/CONTAINERS/sph $SCRATCH/CONTAINERS/
            '## rsync -av %s $SCRATCH/CONTAINERS/' % container_platform_projectdir,
            # TODO: how long does it take to cp large .sif file locally for each test ?
            # TODO: speed of pulled image instead of localimage ?
            # 'echo starttime=`date +%s`',
        ]
        ## self.postrun_cmds = []
        self.executable = container_d['runtime']
        # f'-n {cubesize} -s {step}'
        # executable_arguments = '-n %s -s %s' % (cubesize, step)
        self.executable_opts = [
            container_platform_options, container_platform_image,
            'bash', '-c', f"'{container_platform_variables} {container_platform_executable} {executable_arguments}'", '2>&1']
# }}}

# {{{ sanity
        # self.sanity_patterns_l = [
        self.sanity_patterns = \
            sn.assert_found(r'Total time for iteration\(0\)', self.stdout)
        # self.sanity_patterns = sn.all(self.sanity_patterns_l)
# }}}

# {{{ performance
        # {{{ internal timers
        # use linux date as timer:
        self.prerun_cmds += ['echo starttime=`date +%s`']
        self.postrun_cmds += ['echo stoptime=`date +%s`']
        # }}}

        # {{{ perf_patterns:
        self.perf_patterns = sn.evaluate(sphs.basic_perf_patterns(self))
        # }}}

        # {{{ reference:
        self.reference = sn.evaluate(sphs.basic_reference_scoped_d(self))
        # self.reference = sn.evaluate(sphsintel.vtune_tool_reference(self))
# }}}
# }}}

    # {{{ hooks
    @rfm.run_before('compile')
    def set_compiler_flags(self):
        self.build_system.cxxflags = \
            self.prgenv_flags[self.current_environ.name]

#    @rfm.run_before('run')
#    def set_launcher(self):
#        self.nativejob_launcher = getlauncher('srun')()
#        # self.prerun_cmds.append(f'echo "... {self.nativejob_launcher} {self.native_executable} {executable_arguments}"')

#     @rfm.run_after('setup')
#     def set_launcher(self):
#         linen = 75
#         tracepoint = r'"%s:%d,domain.clist[0],domain.clist"' % \
#                      (self.sourcepath, linen)
#         # recommending tracepoint but this will work too:
#         # --break-at %s:%d --evaluate="domain.clist;domain.clist[0]"
#         self.ddt_options = ['--offline', '--output=%s' % self.htm_rpt,
#                             '--trace-at', tracepoint]
#         self.job.launcher = LauncherWrapper(self.job.launcher, 'ddt',
#                                             self.ddt_options)
    # }}}
# }}}


# {{{ class MPI_Compute_Singularity_Test:
@rfm.parameterized_test(*[[mpi_task, step]
                          for mpi_task in mpi_tasks
                          for step in steps
                          ])
class MPI_Compute_Singularity_Test(SphExaSingularityCheckBase):
    # {{{
    '''
    This class run the executable with Singularity
    (and natively too for comparison)
    '''
    # }}}

    def __init__(self, mpi_task, step):
        # share args with TestBase class
        self.name = f'compute_singularity_{mpi_task}mpi_{step}steps'
        # self.name = 'sphexa_singularity_{}_{:03d}mpi_{:03d}omp_{}step'.format(
        #     self.testname, mpi_task, ompthread, step)
        self.step = step
        self.mpi_task = mpi_task
        cubesize = size_dict[mpi_task]
        container_d = {
            'modulefiles': 'singularity/3.5.3-daint',
            'runtime': 'singularity',
            'options': 'exec',
            'projectdir': '/project/csstaff/piccinal/CONTAINERS/sph',
            'scratch': '$SCRATCH/CONTAINERS/sph',
            'image': 'ub1804_cuda102_mpich314_gnu8+sph.sif',
            'variables': '',
            'mount': '',  # '-B"/x:/x"'
            'executable': '/home/bin/gnu8/mpi+omp.app',
            'executable_opts': f'-n {cubesize} -s {step}'
        }
        self.variables['SINGULARITYENV_LD_LIBRARY_PATH'] = '/opt/gcc/8.3.0/snos/lib64:$SINGULARITYENV_LD_LIBRARY_PATH'
        super().__init__(mpi_task, step, container_d)
        # self.valid_systems = ['dom:mc', 'dom:gpu']
        # {{{ --- run the native executable too:
        nativejob_launcher = 'srun'
        # self.nativejob_stdout = 'rfm_native_job.out'
        # TODO: self.nativejob_launcher = self.current_partition.launcher
        postrun_cmds = [
            # native app:
            # f'ldd {self.native_executable}',
            f'echo starttime=`date +%s` > {nativejob_stdout} 2>&1',
            f"{nativejob_launcher} {self.native_executable} {container_d['executable_opts']} >> {nativejob_stdout} 2>&1",
            f'echo stoptime=`date +%s` >> {nativejob_stdout} 2>&1',
        ]
        self.postrun_cmds.extend(postrun_cmds)
        # }}}
        self.rpt = None
# }}}


# {{{ class MPI_Collect_Logs_Test:
@rfm.simple_test
class MPI_Collect_Logs_Test(rfm.RunOnlyRegressionTest):
    def __init__(self):
        self.name = 'postproc_containers'
        self.valid_systems = ['*']
        self.valid_prog_environs = ['*']
        self.sourcesdir = None
        self.modules = []
        self.num_tasks_per_node = 1
        self.num_tasks = 1
        self.executable = 'echo "collecting jobs stdout"'
        self.sanity_patterns = sn.assert_not_found(r'error', self.stdout)
        # construct list of dependencies from container1 (based on testname):
        # self.name = f'compute_singularity_{mpi_task}mpi_{step}steps'
        #self.testnames_native = [f'compute_{mpi_task}mpi_{step}steps' for step in steps for mpi_task in mpi_tasks]
        #for test in self.testnames_native:
        #    self.depends_on(test)
        # construct list of dependencies from container2 (based on testname):
        # self.testnames_singularity = [f'compute_singularity_{mpi_task}mpi_{step}steps' for step in steps for mpi_task in mpi_tasks]
        self.testnames_singularity = [f'compute_singularity_{mpi_task}mpi_{step}steps' for step in steps for mpi_task in mpi_tasks]
        for test in self.testnames_singularity:
            self.depends_on(test)

    @rfm.require_deps
    def collect_logs(self):
        job_out = '*_job.out'
        # singularity test logs:
        for test_index in range(len(self.testnames_singularity)):
            stagedir = self.getdep(self.testnames_singularity[test_index]).stagedir
            self.postrun_cmds.append(f'cp {stagedir}/{job_out} .')

    @rfm.run_after('run')
    def extract_data(self):
        ftgin=open(os.path.join(self.stagedir, 'timings.rpt'), "w")
        # termgraph header:
        # ftgin.write('# Elapsed_time (seconds) = f(mpi_tasks)\n')
        ftgin.write('@ native,singularity\n')
        #no: ftgin.write('@ mpi,native,singularity\n')
        job_out = 'job.out'
        # TODO: reuse self.testnames_native here
        for step in steps:
            for mpi_task in mpi_tasks:
                # native:
                # testname = self.nativejob_stdout
                self.rpt = os.path.join(self.stagedir, nativejob_stdout)
                res_native = sn.evaluate(sphs.elapsed_time_from_date(self))
                ### rfm_postproc_containers_job.out: No such file or directory
                ### --> update sphs.elapsed_time_from_date with self.rpt
                # singularity:
                testname = f'compute_singularity_{mpi_task}mpi_{step}steps'
                self.rpt = os.path.join(self.stagedir, f'rfm_{testname}_{job_out}')
                res_singularity = sn.evaluate(sphs.elapsed_time_from_date(self))
                # termgraph data:
                ftgin.write(f'{mpi_task},{res_native},{res_singularity}\n')
        ftgin.close()
# }}}


# {{{ class MPI_PostprocTest:
@rfm.simple_test
class MPI_Plot_Test(rfm.RunOnlyRegressionTest):
    def __init__(self):
        self.name = 'performance_containers'
        self.sourcesdir = 'src/scripts'
        # This test will be skipped if --system does not match:
        self.valid_systems = ['dom:mc', 'dom:gpu']
        self.valid_prog_environs = ['*']
        # self.prerun_cmds = ['module use /users/piccinal/easybuild/dom/haswell/modules/tools']
        self.modules = ['termgraph/0.3.1-python3']
        # self.depends_on('MPI_CollectLogsTest')
        self.depends_on('postproc_containers')
        self.executable = 'python3.7'
        # rpt = os.path.join(self.stagedir, 'timings.rpt')
        # tgraph = os.path.join(self.stagedir, 'scripts', 'termgraph_cscs.py')
        # self.postrun_cmds = [f'echo {tgraph} {rpt}']
        self.sanity_patterns = sn.assert_not_found(r'ordinal not in range', self.stderr)

    @rfm.require_deps
    def plot_logs(self):
        # stagedir = self.getdep('MPI_Collect_Logs_Test').stagedir
        stagedir = self.getdep('postproc_containers').stagedir
        rpt = os.path.join(stagedir, 'timings.rpt')
        tgraph = os.path.join(self.stagedir, 'termgraph_cscs.py')
        # tgraph = os.path.join(self.stagedir, 'scripts', 'termgraph_cscs.py')
        self.executable_opts = [f'{tgraph}', f'{rpt}', '--color', '{green,red}', '--suffix', 's', '--title', '"Elapsed time (seconds)"']

# }}}
