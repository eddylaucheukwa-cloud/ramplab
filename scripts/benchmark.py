"""Bounded extraction timing on one reproducible 20,000-pixel sample."""
from pathlib import Path
import json
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ramplab import clustering
from ramplab.tonal_analysis import tonal_palette

rgb = [(i%257/256,(i*7)%257/256,(i*17)%257/256) for i in range(20000)]
results = {'samples':len(rgb),'python':sys.version.split()[0]}
for name,func in [('dominant_numpy',lambda:clustering.dominant_palette(rgb,8)),
                  ('tonal_numpy',lambda:tonal_palette(rgb,8))]:
    start = time.perf_counter()
    output = func()
    results[name] = {'seconds':round(time.perf_counter()-start,3),'colors':len(output)}
with patch.object(clustering,'np',None):
    start = time.perf_counter()
    output = clustering.dominant_palette(rgb,8)
    results['dominant_without_numpy'] = {'seconds':round(time.perf_counter()-start,3),'colors':len(output)}
(ROOT/'test-results'/'benchmark.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
