"""Nonattachment assumptions and experiment settings shared by all stages."""
import json
from functools import lru_cache
from mountain_flood.paths import ROOT

@lru_cache(None)
def base_parameters():
    return json.loads((ROOT / 'config' / 'base_parameters.json').read_text(encoding='utf-8'))

@lru_cache(None)
def optimization_parameters():
    return json.loads((ROOT / 'config' / 'optimization_parameters.json').read_text(encoding='utf-8'))
