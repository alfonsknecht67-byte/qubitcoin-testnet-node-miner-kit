"""Custom-layout updates in disposable homes; services/RPC are simulated."""
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('manual_update', ROOT/'manual-starter-update.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux-only starter update')
class ManualUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)/'home'; self.home.mkdir()
        self.base = self.home/'custom-testnet'; self.base.mkdir()
        self.home_patch = patch.object(Path, 'home', return_value=self.home)
        self.home_patch.start(); self.addCleanup(self.home_patch.stop)
        self.files = {'bin/start-miner.py':b"# original launcher, never executed\nminer = str(base / 'miner-source/qubitcoin-miner')\n",
                      'miner-source/qubitcoin-miner':b'synthetic binary, never executed',
                      'data/testnet/.cookie':b'synthetic:unused',
                      'data/testnet/wallet-marker':b'leave wallet unchanged',
                      'mining-address.txt':b'synthetic-not-a-wallet',
                      'miner-settings.json':json.dumps({'tasks':{'qhash-cpu':{'threads':2},'deqode':{'threads':1}}}).encode()}
        for task,name,count in [('qhash-cpu','miner-local.json',2),('deqode','miner-deqode-local.json',1)]:
            self.files[name] = json.dumps({'algo':task,'url':'http://127.0.0.1:18452',
                'coinbase-addr':'synthetic-not-a-wallet','threads':count,'user':'synthetic','pass':'unused'}).encode()
        for name,data in self.files.items():
            path=self.base/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);path.chmod(0o600)
        self.services={'qhash-cpu':'example-testnet-miner.service','deqode':'example-testnet-deqode.service'}
        self.calls=[]

    def service(self,name):
        self.calls.append(name)
        task=next(t for t,s in self.services.items() if s==name)
        return '{ path=/usr/bin/python3 ; argv[]=/usr/bin/python3 '+str(self.base/'bin/start-miner.py')+' --task '+task+' ; ignore_errors=no ; }'

    def inspect(self,base=None,services=None,chain='test'):
        return m.inspect(base or self.base,services or self.services,self.service,lambda base:chain)

    def test_check_is_read_only(self):
        before={p.relative_to(self.base):p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        state=self.inspect()
        after={p.relative_to(self.base):p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
        self.assertEqual(state['configured_workers'],{'qhash-cpu':2,'deqode':1})
        self.assertFalse(state['worker_counts_differ'])

    def test_main_chain_rejected(self):
        with self.assertRaises(m.UpdateError):self.inspect(chain='main')
        self.assertFalse(list(self.base.glob('manual-kit-update.*')))

    def test_external_rpc_rejected_before_chain_read(self):
        path=self.base/'miner-local.json';cfg=json.loads(path.read_text());cfg['url']='http://example.invalid:18452';path.write_text(json.dumps(cfg))
        with patch.object(m,'read_chain') as rpc, self.assertRaises(m.UpdateError):self.inspect()
        rpc.assert_not_called()

    def test_wrong_payout_rejected_without_printing_value(self):
        path=self.base/'miner-local.json';cfg=json.loads(path.read_text());cfg['coinbase-addr']='different';path.write_text(json.dumps(cfg))
        with self.assertRaises(m.UpdateError) as error:self.inspect()
        self.assertNotIn('different',str(error.exception))

    def test_mainnet_service_rejected(self):
        for name in ['qubitcoin-node.service','main-testnet-miner.service']:
            with self.subTest(name=name),self.assertRaises(m.UpdateError):
                self.inspect(services={'qhash-cpu':name})

    def test_wrong_service_arguments_rejected(self):
        def bad(name):return '{ path=/usr/bin/python3 ; argv[]=/usr/bin/python3 '+str(self.base/'bin/start-miner.py')+' --task qhash-cpu --unexpected ; }'
        with self.assertRaises(m.UpdateError):m.inspect(self.base,self.services,bad,lambda base:'test')

    def test_prepare_protects_backup_and_leaves_live_files(self):
        state=self.inspect();directory=m.prepare(state)
        self.assertEqual(directory.stat().st_mode & 0o777,0o700)
        self.assertEqual((directory/'plan.json').stat().st_mode & 0o777,0o600)
        self.assertEqual((directory/'original/bin/start-miner.py').read_bytes(),self.files['bin/start-miner.py'])
        self.assertFalse((directory/'original/data/testnet/.cookie').exists())
        for name,data in self.files.items():self.assertEqual((self.base/name).read_bytes(),data)

    def test_install_and_rollback_change_only_starter(self):
        state=self.inspect();directory=m.prepare(state)
        m.apply_prepared(directory,inspector=self.inspect)
        self.assertEqual((self.base/'bin/start-miner.py').read_bytes(),state['_candidate'])
        self.assertIn('Already',m.apply_prepared(directory,inspector=self.inspect))
        for name,data in self.files.items():
            if name!='bin/start-miner.py':self.assertEqual((self.base/name).read_bytes(),data)
        m.apply_prepared(directory,rollback=True,inspector=self.inspect)
        self.assertEqual((self.base/'bin/start-miner.py').read_bytes(),self.files['bin/start-miner.py'])

    def test_settings_change_blocks_install(self):
        directory=m.prepare(self.inspect())
        (self.base/'miner-settings.json').write_text('{"threads":3}')
        with self.assertRaises(m.UpdateError):m.apply_prepared(directory,inspector=self.inspect)
        self.assertEqual((self.base/'bin/start-miner.py').read_bytes(),self.files['bin/start-miner.py'])

    def test_candidate_tampering_blocks_install(self):
        directory=m.prepare(self.inspect());(directory/'new-start-miner.py').write_text('# tampered')
        with self.assertRaises(m.UpdateError):m.apply_prepared(directory,inspector=self.inspect)

    def test_live_launcher_change_blocks_install(self):
        directory=m.prepare(self.inspect());(self.base/'bin/start-miner.py').write_text('# edited later')
        with self.assertRaises(m.UpdateError):m.apply_prepared(directory,inspector=self.inspect)

    def test_nonprivate_plan_directory_rejected(self):
        directory=m.prepare(self.inspect());directory.chmod(0o755)
        with self.assertRaises(m.UpdateError):m.apply_prepared(directory,inspector=self.inspect)

    def test_symlink_launcher_rejected(self):
        target=self.home/'outside.py';target.write_text('# outside')
        live=self.base/'bin/start-miner.py';live.unlink();live.symlink_to(target)
        with self.assertRaises(m.UpdateError):self.inspect()

    def test_rpc_uses_only_fixed_local_read_method(self):
        seen=[]
        class Opener:
            def open(self,request,timeout):
                seen.append(request)
                return io.BytesIO(b'{"result":{"chain":"test"},"error":null}')
        with patch.object(m.urllib.request,'build_opener',return_value=Opener()) as build:
            self.assertEqual(m.read_chain(self.base),'test')
        self.assertEqual(seen[0].full_url,'http://127.0.0.1:18452')
        self.assertEqual(json.loads(seen[0].data)['method'],'getblockchaininfo')
        self.assertEqual(build.call_args.args[0].proxies,{})
        self.assertIsNone(build.call_args.args[1].redirect_request(None,None,None,None,None,None))

    def test_versioned_executable_selection_is_preserved(self):
        binary=self.base/'miner-versions/verified/qubitcoin-miner'
        binary.parent.mkdir(parents=True);binary.write_bytes(b'versioned executable, never run')
        live=self.base/'bin/start-miner.py';live.write_text('miner = '+repr(str(binary))+'\n')
        original=live.read_bytes();state=self.inspect()
        self.assertEqual(state['miner_binary_relative'],'miner-versions/verified/qubitcoin-miner')
        self.assertIn(b'miner-versions/verified/qubitcoin-miner',state['_candidate'])
        directory=m.prepare(state)
        m.apply_prepared(directory,inspector=self.inspect)
        self.assertEqual(self.inspect()['miner_binary_sha256'],m.sha(binary.read_bytes()))
        m.apply_prepared(directory,rollback=True,inspector=self.inspect)
        self.assertEqual(live.read_bytes(),original)

    def test_dynamic_executable_selection_is_rejected(self):
        (self.base/'bin/start-miner.py').write_text('miner = choose_binary()\n')
        with self.assertRaises(m.UpdateError):self.inspect()

    def test_active_binary_mismatch_is_rejected(self):
        real_sha=m.sha_file
        def sha_file(path):return '0'*64 if str(path).startswith('/proc/') else real_sha(path)
        def reader(name):return self.service(name)+'\nMainPID=123\n'
        with patch.object(m,'sha_file',side_effect=sha_file),self.assertRaises(m.UpdateError):
            m.inspect(self.base,self.services,reader,lambda base:'test')

    def test_binary_changed_after_preparation_is_rejected(self):
        directory=m.prepare(self.inspect())
        (self.base/'miner-source/qubitcoin-miner').write_bytes(b'changed binary')
        with self.assertRaises(m.UpdateError):m.apply_prepared(directory,inspector=self.inspect)

    def test_root_owned_folder_stops_with_narrow_repair_hint(self):
        real_stat=Path.stat;directory=self.base/'bin'
        def fake_stat(path,*args,**kwargs):
            value=real_stat(path,*args,**kwargs)
            if path==directory:
                fields=list(value);fields[4]=0;fields[5]=0
                return os.stat_result(fields)
            return value
        with patch.object(Path,'stat',fake_stat),patch.object(m.os,'access',return_value=False),self.assertRaises(m.UpdateError) as error:
            self.inspect()
        message=str(error.exception)
        self.assertIn('--no-dereference',message)
        self.assertIn(str(directory),message)
        self.assertNotIn('--recursive',message)
        self.assertEqual((self.base/'bin/start-miner.py').read_bytes(),self.files['bin/start-miner.py'])

    def test_unknown_folder_permissions_stop_without_repair_command(self):
        with patch.object(m.os,'access',return_value=False),self.assertRaises(m.UpdateError) as error:self.inspect()
        self.assertIn('administrator review',str(error.exception))
        self.assertNotIn('sudo',str(error.exception))


if __name__=='__main__':unittest.main(verbosity=2)
