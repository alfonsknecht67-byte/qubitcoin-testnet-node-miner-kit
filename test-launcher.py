"""Exercise launcher settings with synthetic secrets; never execute a miner."""
import json
import runpy
import tempfile
from pathlib import Path
from unittest.mock import patch

launcher = Path(__file__).with_name('start-miner.py')
with tempfile.TemporaryDirectory() as temp:
    home = Path(temp); base = home / 'qubitcoin-community-testnet'
    (base / 'data/testnet').mkdir(parents=True)
    (base / 'data/testnet/.cookie').write_text('synthetic:unused')
    (base / 'mining-address.txt').write_text('synthetic-unused-address')
    def launch(settings=None):
        f = base / 'miner-settings.json'
        if settings is None:
            f.unlink(missing_ok=True)
        else:
            f.write_text(json.dumps(settings))
        with patch.object(Path, 'home', return_value=home), patch('os.execv') as execute:
            runpy.run_path(str(launcher))
            execute.assert_called_once()
            assert execute.call_args.args[0] == str(base/'miner-source/qubitcoin-miner')
        return json.loads((base/'miner-local.json').read_text())
    assert launch()['threads'] == 1
    configured = launch({'threads': 7, 'affinity': 'off'})
    assert configured['threads'] == 7 and configured['cpu-affinity'] == '0'
    assert launch({'threads': 3, 'affinity': 'auto'})['threads'] == 3
    assert 'cpu-affinity' not in launch({'threads': 3, 'affinity': 'auto'})
    for bad in [0, -1, True, '4', 10000]:
        try:
            launch({'threads': bad})
        except SystemExit:
            pass
        else:
            raise AssertionError('invalid thread setting accepted')
print('PASS: default/persistent worker settings, affinity opt-out, validation; no miner executed.')
