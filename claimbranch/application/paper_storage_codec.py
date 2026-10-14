"""Version-selected personal storage; legacy and provider codecs stay bounded."""
from claimbranch.core import canonical
from claimbranch.core.paper_capacity import encode as paper_encode, decode as paper_decode
from claimbranch.core.research_schema import normalize as schema_normalize

SCHEMAS = {'claimbranch.paper-work/v22','claimbranch.project-work/v18','claimbranch.paper-work/v21','claimbranch.project-work/v17','claimbranch.paper-work/v20','claimbranch.project-work/v16','claimbranch.paper-work/v19','claimbranch.project-work/v15','claimbranch.paper-work/v18','claimbranch.project-work/v14','claimbranch.paper-work/v17','claimbranch.project-work/v13','claimbranch.paper-work/v14', 'claimbranch.project-work/v10',
           'claimbranch.paper-workspace/v13', 'claimbranch.paper-work/v15', 'claimbranch.project-work/v11', 'claimbranch.paper-workspace/v14','claimbranch.paper-work/v16','claimbranch.project-work/v12','claimbranch.paper-workspace/v15'}


def is_paper(value):
    return type(value) is dict and (value.get('schema') in SCHEMAS or value.get('schema_version') in (4, 5, 6, 7, 8, 9, 10, 11, 12))


def encode(value):
    return paper_encode(value, purpose='project') if is_paper(value) else canonical.canonical_bytes(value)


def decode(raw):
    value = paper_decode(raw, purpose='project')
    return value if is_paper(value) else canonical.decode(raw)


def normalize(value, schema):
    return schema_normalize(value, schema, profile='paper' if is_paper(value) else 'episode')
