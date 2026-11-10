"""Synthetic resource/benchmark tests. No real miner, affinity change or RPC."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


plan = load('plan', 'resource_plan.py')
bench = load('bench', 'bench/run_offline.py')


def resources(n=8, ram=8*plan.MIB*1024, quota=None):
    return {'allowed_cpus': list(range(n)), 'core_representatives': list(range(n)),
            'topology_complete': True, 'available_memory_bytes': ram,
            'cpu_quota': quota, 'warnings': []}


class PlannerTests(unittest.TestCase):
    def test_balanced_disjoint_with_reserve(self):
        r = plan.recommend(resources(), profile='balanced')
        q, d = (r['suggested_settings']['tasks'][t] for t in plan.TASKS)
        self.assertEqual(q['threads'] + d['threads'], 6)
        self.assertFalse(set(q['cpu-set']) & set(d['cpu-set']))
        self.assertEqual(r['reserved_capacity_units'], 2)
        self.assertEqual(d['deqode-memory-mib'], 64)

    def test_background_smaller(self):
        self.assertEqual(plan.recommend(resources())['workers_recommended'], 4)

    def test_large_sparse_cpu_ids(self):
        r = resources(4)
        r['allowed_cpus'] = r['core_representatives'] = [2,64,1024,2048]
        chosen = plan.recommend(r)['suggested_settings']['tasks']
        self.assertEqual([chosen[t]['cpu-set'] for t in plan.TASKS], [[2],[64]])

    def test_quota_limits_workers(self):
        r = plan.recommend(resources(64, quota=2.5))
        self.assertEqual(r['workers_recommended'], 1)
        self.assertTrue(r['inactive_tasks'])

    def test_fractional_quota_warns(self):
        self.assertIn('Fractional CPU quota', ' '.join(plan.recommend(resources(quota=0.5))['warnings']))

    def test_low_memory_can_recommend_no_mining(self):
        r = plan.recommend(resources(ram=128*plan.MIB))
        self.assertEqual(r['workers_recommended'], 0)
        self.assertEqual(r['suggested_settings']['tasks'], {})

    def test_unknown_memory_never_many_workers(self):
        self.assertEqual(plan.recommend(resources(64, ram=None))['workers_recommended'], 1)

    def test_no_affinity_guess_on_windows(self):
        r = resources(); r['allowed_cpus'] = None
        for task in plan.recommend(r)['suggested_settings']['tasks'].values():
            self.assertNotIn('cpu-set', task)

    def test_invalid_limits(self):
        for quota in [True,0,-1,float('nan'),float('inf')]:
            with self.subTest(quota=quota), self.assertRaises(ValueError):
                plan.recommend(resources(quota=quota))
        for workers in [0,5,True]:
            with self.subTest(workers=workers), self.assertRaises(ValueError):
                plan.recommend(resources(), workers=workers)

    def test_unknown_or_duplicate_tasks(self):
        for tasks in [(), ('other',), ('deqode','deqode')]:
            with self.subTest(tasks=tasks), self.assertRaises(ValueError):
                plan.recommend(resources(), tasks=tasks)

    def test_detect_smt_quota_and_cgroup_memory(self):
        def read(path):
            path = str(path).replace('\\','/')
            if path.endswith('physical_package_id'): return '0'
            if path.endswith('core_id'): return '0' if '/cpu0/' in path or '/cpu1/' in path else '1'
            return {'/proc/meminfo':'MemAvailable: 8388608 kB',
                    '/proc/self/cgroup':'0::/test', '/sys/fs/cgroup/cgroup.controllers':'cpu memory',
                    '/sys/fs/cgroup/test/cpu.max':'150000 100000',
                    '/sys/fs/cgroup/test/memory.max':str(1024*plan.MIB),
                    '/sys/fs/cgroup/test/memory.current':str(256*plan.MIB)}.get(path)
        with patch.object(plan.os,'sched_getaffinity',return_value={0,1,2,3},create=True), patch.object(plan,'read_text',side_effect=read):
            r = plan.detect()
        self.assertEqual(r['core_representatives'], [0,2])
        self.assertEqual(r['cpu_quota'], 1.5)
        self.assertEqual(r['available_memory_bytes'], 768*plan.MIB)


class BenchmarkTests(unittest.TestCase):
    def sample(self, task='qhash-cpu'):
        return {'task':task,'fixture':'synthetic-v1','units':8 if task=='qhash-cpu' else 256,
                'unit':'circuit_simulations' if task=='qhash-cpu' else 'syndromes_processed',
                'seconds':1.0,'correctness_checks':True,'validated_witnesses':2,'checksum':0.5}

    def test_valid_sample(self):
        for task in bench.TASKS:
            self.assertIs(bench.validate_sample(self.sample(task),task,8)['correctness_checks'],True)

    def test_bad_or_partial_sample_rejected(self):
        for field,value in [('seconds',0),('seconds',float('nan')),('units',7),('units',True),('correctness_checks',False),('task','deqode'),('checksum',float('inf'))]:
            sample=self.sample();sample[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                bench.validate_sample(sample,'qhash-cpu',8)
        sample=self.sample('deqode');sample['validated_witnesses']=0
        with self.assertRaises(ValueError):bench.validate_sample(sample,'deqode',8)

    def test_concurrent_commands_only_target_offline_binary(self):
        calls=[]
        def fake(cmd,**kwargs):
            calls.append(cmd)
            return SimpleNamespace(stdout=json.dumps(self.sample()))
        with patch.object(bench.shutil,'which',side_effect=lambda x:'/usr/bin/'+x):
            case=bench.run_case(Path('/tmp/test/qtc-offline-kernels'),'qhash-cpu',[2,1024],8,runner=fake)
        self.assertEqual(case['units'],16)
        self.assertEqual(case['workers'],2)
        for cmd in calls:
            self.assertEqual(cmd[:5],['/usr/bin/nice','-n','19','/usr/bin/taskset','-c'])
            self.assertEqual(cmd[-3:],[str(Path('/tmp/test/qtc-offline-kernels')),'qhash-cpu','8'])

    def test_comparison_rejects_different_fixtures(self):
        base={'workers':1,'fixture':'a','unit':'x','rounds_per_worker':8,'units_per_wall_second':10,'wall_seconds':1}
        with self.assertRaises(ValueError):bench.summarize([base,{**base,'fixture':'b'}])

    def test_summary_medians_and_short_warning(self):
        rows=[{'workers':w,'fixture':'a','unit':'x','rounds_per_worker':8,
               'units_per_wall_second':rate,'wall_seconds':duration}
              for w,rate,duration in [(1,10,1),(1,20,1),(2,30,0.1)]]
        result=bench.summarize(rows)
        self.assertEqual(result[0]['median_units_per_wall_second'],15)
        self.assertEqual(result[1]['speedup_vs_one_worker'],2)
        self.assertTrue(result[1]['short_samples'])

    def test_tampered_binary_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)
            (directory/'qtc-offline-kernels').write_bytes(b'not an executable')
            (directory/'build-manifest.json').write_text(json.dumps({'binary_sha256':'0'*64}))
            with self.assertRaises(ValueError):bench.verify_build(directory)

    def test_default_is_dry_run(self):
        result=subprocess.run([sys.executable,str(ROOT/'bench/run_offline.py'),'--build-dir','does-not-exist','--task','qhash-cpu'],capture_output=True,text=True,check=True)
        self.assertTrue(json.loads(result.stdout)['dry_run'])


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux-only launcher dependency')
class LauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.launch=load('resource_launcher','start-miner.py')

    def settings(self):
        return {'tasks':{'qhash-cpu':{'threads':1,'cpu-set':[2]},
                         'deqode':{'threads':1,'cpu-set':[1024],'deqode-memory-mib':32}}}

    def test_disjoint_sets_and_memory(self):
        self.assertEqual(self.launch.resource_settings(self.settings(),'deqode',{2,1024}),({1024},32))

    def test_overlap_unavailable_and_invalid_sets(self):
        for cpus in [[2],[],[True],[1024,1024],[-1],['2']]:
            settings=self.settings();settings['tasks']['deqode']['cpu-set']=cpus
            with self.subTest(cpus=cpus),self.assertRaises(ValueError):
                self.launch.resource_settings(settings,'deqode',{2,1024})
        with self.assertRaises(ValueError):self.launch.resource_settings(self.settings(),'deqode',{2})

    def test_memory_limits(self):
        for memory in [0,-1,True,'64',4097]:
            settings=self.settings();settings['tasks']['deqode']['deqode-memory-mib']=memory
            with self.subTest(memory=memory),self.assertRaises(ValueError):
                self.launch.resource_settings(settings,'deqode',{2,1024})

    def test_future_launcher_affinity_and_config_exec_all_mocked(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp);base=home/'qubitcoin-community-testnet'
            (base/'data/testnet').mkdir(parents=True)
            (base/'data/testnet/.cookie').write_text('synthetic:unused')
            (base/'mining-address.txt').write_text('synthetic-unused-address')
            (base/'miner-settings.json').write_text(json.dumps(self.settings()))
            with patch.object(Path,'home',return_value=home),patch.object(self.launch.os,'sched_getaffinity',return_value={2,1024}),patch.object(self.launch.os,'sched_setaffinity') as affinity,patch.object(self.launch.os,'execv') as execute:
                self.launch.main(['--task','deqode'])
                affinity.assert_called_once_with(0,{1024})
                execute.assert_called_once()
            config=json.loads((base/'miner-deqode-local.json').read_text())
            self.assertEqual(config['deqode-mem'],32)
            self.assertEqual(config['cpu-affinity'],'0')


if __name__=='__main__':
    unittest.main(verbosity=2)
