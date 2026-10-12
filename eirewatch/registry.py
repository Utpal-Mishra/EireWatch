"""Configuration evidence gates, not authentication or legal certification."""
import math
from urllib.parse import urlsplit


def positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def validate_config(config):
    required = {'id', 'url', 'adapter', 'max_age_hours', 'approved_for_ingestion', 'official'}
    if not isinstance(config, dict) or not required <= config.keys():
        raise ValueError('Missing source configuration')
    if not isinstance(config['id'], str) or not config['id'].strip():
        raise ValueError('Source identity required')
    for key in ('approved_for_ingestion', 'official'):
        if type(config[key]) is not bool:
            raise ValueError('Source flags must be booleans')
    if not positive(config['max_age_hours']):
        raise ValueError('Positive finite collection age required')
    if 'publication_max_age_hours' in config and not positive(config['publication_max_age_hours']):
        raise ValueError('Positive finite publication age required')
    if type(config.get('synthetic', False)) is not bool:
        raise ValueError('Synthetic flag must be boolean')
    if config.get('synthetic', False) or not config['approved_for_ingestion']:
        return
    if config['adapter'] != 'normalized-json-v1':
        raise ValueError('Adapter has not been implemented')
    if 'publication_max_age_hours' not in config:
        raise ValueError('Production publication policy required')
    approval = config.get('approval', {})
    if not isinstance(approval, dict):
        raise ValueError('Approval must be an object')
    for key in ('publisher', 'endpoint_evidence_url', 'reuse_terms_url', 'reuse_notes',
                'reviewed_at', 'reviewer', 'adapter_test_evidence'):
        if not isinstance(approval.get(key), str) or not approval[key].strip():
            raise ValueError('Production approval evidence incomplete')
    from .core import instant
    instant(approval['reviewed_at'])
    for key in ('endpoint_verified', 'reuse_verified', 'adapter_verified'):
        if approval.get(key) is not True:
            raise ValueError('Production source verification incomplete')
    for url in (config['url'], approval['endpoint_evidence_url'], approval['reuse_terms_url']):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('HTTPS evidence and endpoint required')
    if urlsplit(config['url']).hostname not in config.get('allowed_hosts', []):
        raise ValueError('Production endpoint must be allowlisted')
