"""Linux tests using synthetic credentials; no real miner or service is executed."""
import importlib.util
import fcntl
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('launcher',ROOT/'start-miner.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as temp:
    home=Path(temp);base=home/'qubitcoin-community-testnet'
    (base/'data/testnet').mkdir(parents=True)
    (base/'data/testnet/.cookie').write_text('synthetic:unused')
    (base/'mining-address.txt').write_text('synthetic-unused-address')
    def launch(settings=None,task='qhash-cpu'):
        f=base/'miner-settings.json'
        if settings is None: f.unlink(missing_ok=True)
        else: f.write_text(json.dumps(settings))
        with patch.object(Path,'home',return_value=home),patch.object(m.os,'execv') as execute:
            m.main(['--task',task]);execute.assert_called_once()
            assert execute.call_args.args[0]==str(base/'miner-source/qubitcoin-miner')
            config=Path(execute.call_args.args[1][1].split('=',1)[1])
            assert config.stat().st_mode & 0o777==0o600
        return json.loads(config.read_text())
    assert launch()['threads']==1
    assert launch({'threads':7,'affinity':'off'})['threads']==7
    assert launch({'threads':80},'deqode')['threads']==1
    assert launch(None,'deqode')['cpu-affinity']=='0'
    settings={'threads':3,'tasks':{'qhash-cpu':{'threads':2},'deqode':{'threads':1,'affinity':'off'}}}
    q=launch(settings);d=launch(settings,'deqode')
    assert q['algo']=='qhash-cpu' and q['threads']==2 and 'cpu-affinity' not in q
    assert d['algo']=='deqode' and d['threads']==1 and d['cpu-affinity']=='0'
    assert json.loads((base/'miner-local.json').read_text())==q
    assert json.loads((base/'miner-deqode-local.json').read_text())==d
    for settings in [{'threads':x} for x in [0,-1,True,'4',10000]] + [{'tasks':[]},{'tasks':{'unknown':{}}},{'tasks':{'deqode':{'affinity':'bad'}}}]:
        try: m.task_settings(settings,'deqode' if 'tasks' in settings else 'qhash-cpu')
        except ValueError: pass
        else: raise AssertionError('invalid settings accepted')
    fd=os.open(base/'miner-qhash-cpu.lock',os.O_CREAT|os.O_RDWR,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try: launch()
        except ValueError: pass
        else: raise AssertionError('duplicate task was allowed')
        assert launch(task='deqode')['algo']=='deqode'
    finally: os.close(fd)
print('PASS: task separation, legacy settings, private config modes, safe defaults, validation, same-task lock; exec mocked.')
