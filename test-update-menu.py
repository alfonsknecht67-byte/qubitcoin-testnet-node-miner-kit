"""Guided update controls, all actual update/service/RPC operations mocked."""
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('update_menu',ROOT/'update-miner.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)


class MenuTests(unittest.TestCase):
    def setUp(self):
        self.base=Path('/home/example/custom-testnet')
        self.services={'qhash-cpu':'example-testnet-miner.service','deqode':'example-testnet-deqode.service'}
        self.output=[]

    def reader(self,name):
        task=next(t for t,s in self.services.items() if s==name)
        return '{ path=/usr/bin/python3 ; argv[]=/usr/bin/python3 '+str(self.base/'bin/start-miner.py')+' --task '+task+' ; }'

    def test_detect_services_from_exact_launcher_not_names_alone(self):
        result=w.identify_services(self.base,list(self.services.values()),self.reader)
        self.assertEqual(result,self.services)
        with self.assertRaises(w.m.UpdateError):
            w.identify_services(self.base,['other-testnet.service'],lambda name:'{ argv[]=/other/launcher ; }')

    def test_exit_at_check_does_not_prepare_or_install(self):
        state={'configured_workers':{'qhash-cpu':1,'deqode':1},'worker_counts_differ':False,'miner_binary_relative':'miner-source/qubitcoin-miner'}
        with patch.object(w.m,'inspect',return_value=state),patch.object(w.m,'prepare') as prepare,patch.object(w.m,'apply_prepared') as install:
            w.update_flow(self.base,list(self.services.values()),lambda prompt:'q',self.output.append,self.reader)
        prepare.assert_not_called();install.assert_not_called()

    def test_prepare_without_confirmation_never_installs(self):
        state={'configured_workers':{'qhash-cpu':1},'worker_counts_differ':False,'miner_binary_relative':'miner-source/qubitcoin-miner'}
        answers=iter(['1',''])
        with patch.object(w.m,'inspect',return_value=state),patch.object(w.m,'prepare',return_value=Path('/tmp/private-backup')),patch.object(w.m,'apply_prepared') as install:
            w.update_flow(self.base,list(self.services.values()),lambda prompt:next(answers),self.output.append,self.reader)
        install.assert_not_called()

    def test_explicit_update_installs_only_prepared_directory(self):
        state={'configured_workers':{'qhash-cpu':1},'worker_counts_differ':False,'miner_binary_relative':'miner-source/qubitcoin-miner'}
        answers=iter(['1','UPDATE']);backup=Path('/tmp/private-backup')
        with patch.object(w.m,'inspect',return_value=state),patch.object(w.m,'prepare',return_value=backup),patch.object(w.m,'apply_prepared',return_value='installed') as install:
            w.update_flow(self.base,list(self.services.values()),lambda prompt:next(answers),self.output.append,self.reader)
        install.assert_called_once_with(backup)

    def test_choose_reprompts_invalid_input(self):
        answers=iter(['wrong','9','1'])
        self.assertEqual(w.choose('Choice',[('one','selected')],lambda prompt:next(answers),self.output.append),'selected')

    def test_detection_checks_files_not_folder_name(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp);base=home/'different-name'
            (base/'bin').mkdir(parents=True);(base/'miner-source').mkdir()
            (base/'bin/start-miner.py').write_text('# synthetic')
            (base/'miner-source/qubitcoin-miner').write_text('synthetic, never executed')
            (home/'unrelated').mkdir()
            self.assertEqual(w.installations(home),[base])

    @unittest.skipUnless(sys.platform.startswith('linux'),'Linux-only end-to-end fixture')
    def test_full_menu_cancel_and_install_in_disposable_home(self):
        inspect_real=w.m.inspect;apply_real=w.m.apply_prepared
        for confirmation in ('','UPDATE'):
            with self.subTest(confirmation=confirmation),tempfile.TemporaryDirectory() as temp:
                home=Path(temp);base=home/'custom-testnet'
                files={'bin/start-miner.py':b"# old starter\nminer = str(base / 'miner-source/qubitcoin-miner')\n",
                       'miner-source/qubitcoin-miner':b'fake binary, never executed',
                       'data/testnet/.cookie':b'synthetic:unused',
                       'data/testnet/wallet-marker':b'preserve wallet',
                       'mining-address.txt':b'synthetic-not-a-wallet',
                       'miner-settings.json':b'{"threads":1}'}
                for task,name in [('qhash-cpu','miner-local.json'),('deqode','miner-deqode-local.json')]:
                    files[name]=json.dumps({'algo':task,'threads':1,'url':'http://127.0.0.1:18452','coinbase-addr':'synthetic-not-a-wallet'}).encode()
                for name,data in files.items():
                    path=base/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);path.chmod(0o600)
                services={'qhash-cpu':'fixture-testnet-miner.service','deqode':'fixture-testnet-deqode.service'}
                def reader(name):
                    task=next(t for t,s in services.items() if s==name)
                    return '{ argv[]=/usr/bin/python3 '+str(base/'bin/start-miner.py')+' --task '+task+' ; }'
                def inspector(selected,selected_services):
                    return inspect_real(selected,selected_services,reader,lambda base:'test')
                answers=iter(['1','1','1',confirmation]);output=[]
                with patch.object(Path,'home',return_value=home),patch.object(w,'list_services',return_value=list(services.values())),patch.object(w.m,'service_command',side_effect=reader),patch.object(w.m,'inspect',side_effect=inspector),patch.object(w.m,'apply_prepared',side_effect=lambda directory,rollback=False:apply_real(directory,rollback,inspector)):
                    self.assertIsNone(w.main(lambda prompt:next(answers),output.append))
                self.assertEqual(len(list(base.glob('manual-kit-update.*'))),1)
                current=(base/'bin/start-miner.py').read_bytes()
                self.assertEqual(current!=files['bin/start-miner.py'],confirmation=='UPDATE')
                for name,data in files.items():
                    if name!='bin/start-miner.py':self.assertEqual((base/name).read_bytes(),data)


if __name__=='__main__':unittest.main(verbosity=2)
