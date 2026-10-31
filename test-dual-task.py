"""Check units, monitor actions and paused/fresh sample handling without touching services."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from datetime import datetime

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
unit=load('units','miner-unit.py');mon=load('monitor','testnet-monitor.py')
for task in mon.SERVICES:
    text=unit.render(Path('/home/test/qubitcoin-community-testnet'),'test',task)
    assert '--task '+task in text and 'UMask=0077' in text
    assert 'Requires=qubitcoin-community-testnet-node.service' in text
    assert ('miner-deqode.log' if task=='deqode' else 'miner.log') in text
for key,(verb,tasks) in mon.ACTIONS.items():
    with patch.object(mon.os,'geteuid',return_value=1000),patch.object(mon.subprocess,'run') as run:
        run.return_value.returncode=0;assert mon.control(key)
        assert run.call_args.args[0]==['sudo','systemctl',verb]+[mon.SERVICES[t] for t in tasks]
        assert all('node.service' not in x for x in run.call_args.args[0])
with patch.object(mon.subprocess,'run') as run:
    assert mon.control('unknown') is False;run.assert_not_called()
with TemporaryDirectory() as temp:
    mon.BASE=Path(temp);now=datetime.now().replace(microsecond=0);stamp=now.strftime('%Y-%m-%d %H:%M:%S')
    (mon.BASE/'miner.log').write_text(f'[{stamp}] Thread 0, CPU 0: 12.5 h/s\n[{stamp}] Thread 1, CPU 2: 1.0 kh/s\n')
    (mon.BASE/'miner-deqode.log').write_text(f'[{stamp}] Thread 0, CPU 0: 3.5 h/s\n')
    assert mon.recent_rate('qhash-cpu',0,now.timestamp())==1012.5
    assert mon.recent_rate('deqode',0,now.timestamp())==3.5
    assert mon.recent_rate('deqode',now.timestamp()+1,now.timestamp()) is None
    assert mon.recent_rate('deqode',0,now.timestamp()+40) is None
    with patch.object(mon,'service_status',return_value=('paused',123)),patch.object(mon,'recent_rate') as rate,patch.object(mon,'command',return_value='{}'):
        mon.show();rate.assert_not_called()
print('PASS: two isolated units, whitelisted task controls, separate/fresh meter samples and paused-state reporting.')
