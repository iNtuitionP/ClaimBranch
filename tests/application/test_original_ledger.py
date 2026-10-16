"""Original maintained ledgers, never private research or a provider request."""
from copy import deepcopy
import json
import unittest
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import encode, source_record, source_bytes
from claimbranch.core.argument_import import preview_import


def fixture():
    raw = '# Argument\r\n\r\n| ID | Claim | Scope |\r\n| --- | --- | --- |\r\n| T | Rubric score is not writing quality. | Synthetic prompts |\r\n| C | Blind preference can fall. | Synthetic prompts |\r\n'.encode()
    def mapping(target, row, column):
        return dict(target=target,file_id='ledger',locator=dict(kind='markdown-cell',heading=['Argument'],row=row,column=column),normalization='cell-trim-v1',transformation=None)
    return dict(schema='claimbranch.argument-import/v2',profile='paper',project_id='P',title='Synthetic argument',
        origin_default=dict(contributor='mixed',detail=None),
        files=[dict(id='ledger',name='claims.md',media='markdown',source=source_record(raw))],
        condition_vocabulary=[],records=[
            dict(id='T',kind='thesis',body=dict(statement='Rubric score is not writing quality.'),recorded_at=None,
                mappings=[[mapping('/statement','T','Claim')]]),
            dict(id='C',kind='claim',body=dict(role='main',statement='Blind preference can fall.',scope='Synthetic prompts',parent_ids=['T'],status='proposed',basis_ids=[]),recorded_at=None,
                mappings=[[mapping('/statement','C','Claim'),mapping('/scope','C','Scope'),
                    dict(target='/parent_ids/0',file_id='ledger',locator=dict(kind='lines',start=1,end=1),normalization='literal-v1',transformation='Declare present-day thesis hierarchy; not recorded in ledger.',source_silent=True),
                    dict(target='/basis_ids',file_id='ledger',locator=dict(kind='lines',start=1,end=1),normalization='literal-v1',transformation='No status basis asserted.',source_silent=True),
                    dict(target='/role',file_id='ledger',locator=dict(kind='lines',start=1,end=1),normalization='literal-v1',transformation='Declare main claim role.',source_silent=True),
                    dict(target='/status',file_id='ledger',locator=dict(kind='lines',start=1,end=1),normalization='literal-v1',transformation='Source has no app status; keep proposed.',source_silent=True)]])],selected_ids=['C'])


class OriginalLedgerTests(unittest.TestCase):
    def preview(self,value=None):return preview_import(encode(value or fixture(),purpose='project'))

    def test_markdown_table_cell_and_original_crlf_are_preserved(self):
        value=fixture();result=self.preview(value)
        self.assertTrue(result['valid'],result.get('errors'))
        self.assertEqual(['T'],result['required']);self.assertTrue(result['registration_available'])
        self.assertEqual(source_bytes(value['files'][0]['source']),source_bytes(result['files'][0]['source']))
        self.assertEqual('normalized-exact',result['records'][0]['coverage'][0]['state'])
        self.assertEqual('mixed',result['records'][0]['effective_origin']['contributor'])

    def test_override_replaces_fallback_but_not_an_independent_source_origin(self):
        value=fixture();value['records'][0]['origin']=dict(contributor='human',detail='Written by researcher.')
        result=self.preview(value);self.assertTrue(result['valid'],result.get('errors'))
        self.assertEqual('human',result['records'][0]['effective_origin']['contributor'])
        self.assertEqual('record',result['records'][0]['effective_origin']['declaration'])

    def test_changed_value_requires_transformation_and_remains_unresolved(self):
        value=fixture();value['records'][0]['body']['statement']='A rounded or rewritten claim.'
        self.assertFalse(self.preview(value)['valid'])
        value['records'][0]['mappings'][0][0]['transformation']='Researcher rewrote the claim.'
        result=self.preview(value);self.assertTrue(result['valid'],result.get('errors'))
        self.assertEqual('transformed',result['records'][0]['coverage'][0]['state'])

    def test_duplicate_heading_or_row_and_broken_unicode_span_are_refused(self):
        for added in (b'\r\n# Argument\r\n',b'| T | Duplicate | Other |\r\n'):
            value=fixture();value['files'][0]['source']=source_record(source_bytes(value['files'][0]['source'])+added)
            self.assertFalse(self.preview(value)['valid'])
        value=fixture();value['files'][0].update(media='text',source=source_record('한국어'.encode()))
        value['records']=value['records'][:1];value['selected_ids']=['T']
        value['records'][0]['mappings'][0][0].update(locator=dict(kind='span',start=1,end=4),normalization='literal-v1')
        self.assertFalse(self.preview(value)['valid'])

    def test_scientific_fields_cannot_claim_derived_structure(self):
        value=fixture();value['records'][0]['mappings']=[[dict(target='/statement',derived='structure-v1')]]
        self.assertFalse(self.preview(value)['valid'])

    def test_multiple_sources_require_joint_origin_and_keep_unknown_with_ai(self):
        value=fixture();other=deepcopy(value['files'][0]);other.update(id='second',origin_default=dict(contributor='unknown',detail=None));value['files'].append(other)
        value['records'][1]['mappings'][0][1]['file_id']='second'
        self.assertFalse(self.preview(value)['valid'])
        value['records'][1]['joint_origin']=dict(contributor='mixed',detail='Both source files influenced this record.')
        result=self.preview(value);self.assertTrue(result['valid'],result.get('errors'))
        origin=result['records'][1]['effective_origin'];self.assertEqual('mixed',origin['contributor']);self.assertTrue(origin['unknown'])

    def test_explicit_second_source_ai_cannot_be_removed_by_human_override(self):
        value=fixture();other=deepcopy(value['files'][0]);other['id']='second';value['files'].append(other)
        record=value['records'][1];record['origin']=dict(contributor='human',detail=None)
        record['mappings'][0][1]['file_id']='second'
        record['source_origins']=[dict(file_id='second',origin=dict(contributor='ai',detail='Explicit source assertion.'))]
        self.assertFalse(self.preview(value)['valid'])
        record['joint_origin']=dict(contributor='human',detail='Attempted relabeling.')
        self.assertFalse(self.preview(value)['valid'])
        record['joint_origin']['contributor']='mixed'
        result=self.preview(value);self.assertTrue(result['valid'],result.get('errors'))
        self.assertEqual('mixed',result['records'][1]['effective_origin']['contributor'])

    def test_literal_pipes_inline_code_and_fences_have_exact_cell_boundaries(self):
        value=fixture();raw=source_bytes(value['files'][0]['source'])
        raw=raw.replace(b'Rubric score is not writing quality.',br'Use \| and `a\|b` literally.')
        raw+=b'\n```md\n# Argument\n| T | Not a table | Wrong |\n```\n'
        value['files'][0]['source']=source_record(raw)
        value['records'][0]['body']['statement']=r'Use \| and `a\|b` literally.'
        self.assertTrue(self.preview(value)['valid'])

    def test_json_leaf_unknown_origin_and_numeric_transform_are_serializable(self):
        value=fixture();value.pop('origin_default');value['records']=value['records'][:1];value['selected_ids']=['T']
        value['files'][0].update(media='json',source=source_record(b'{"value":0.1250}'))
        value['records'][0]['mappings'][0][0].update(locator=dict(kind='json-pointer',pointer='/value'),normalization='literal-v1',transformation='Interpret the numeric result in prose.')
        result=self.preview(value);self.assertTrue(result['valid'],result.get('errors'))
        self.assertEqual('unknown',result['records'][0]['effective_origin']['contributor']);json.dumps(result)
        value['records'][0]['mappings'][0][0]['locator']['pointer']=''
        self.assertFalse(self.preview(value)['valid'])

    def test_preview_limits_extraction_and_never_builds_a_v1_saved_seed(self):
        from claimbranch.core.argument_import import history_from_import
        value=fixture()
        self.assertEqual(14,history_from_import(encode(value,purpose='project'),anchor_id='anchor').schema_version)
        value['files'][0].update(media='text',source=source_record(b'x'*20000))
        value['records']=value['records'][:1];value['selected_ids']=['T']
        value['records'][0]['mappings'][0][0].update(locator=dict(kind='span',start=0,end=20000),normalization='literal-v1',transformation='Summarize source')
        self.assertFalse(self.preview(value)['valid'])

    def test_absent_headings_and_json_failures_do_not_repeat_source_scans(self):
        from unittest.mock import patch
        from claimbranch.core.argument_sources import SourceResolver,_markdown_index
        import json
        raw=source_bytes(fixture()['files'][0]['source']);resolver=SourceResolver(raw,'markdown')
        with patch('claimbranch.core.argument_sources._markdown_index',wraps=_markdown_index) as parser:
            for i in range(1000):
                with self.assertRaises(ContractError):resolver.resolve(dict(kind='markdown-cell',heading=[f'absent-{i}'],row='T',column='Claim'))
            self.assertEqual(1,parser.call_count)
        resolver=SourceResolver(json.dumps(list(range(2049))).encode(),'json')
        with patch('json.loads',wraps=json.loads) as parser:
            for i in range(100):
                with self.assertRaisesRegex(ContractError,'collection'):resolver.resolve(dict(kind='json-pointer',pointer='/0'))
            self.assertEqual(1,parser.call_count)
        resolver=SourceResolver(raw,'markdown',dict(markdown_cells=131072))
        for _ in range(2):
            with self.assertRaisesRegex(ContractError,'capacity'):resolver.resolve(dict(kind='markdown-cell',heading=['Argument'],row='T',column='Claim'))
        self.assertEqual(131073,resolver.budget['markdown_cells'])

    def test_fence_closers_setext_and_unicode_line_separators_are_literal(self):
        from claimbranch.core.argument_sources import SourceResolver
        raw=b'# Argument\n```md\n```python\n| ID | Claim |\n| --- | --- |\n| T | code sample |\n```\n\nTitle\n=====\n| ID | Claim |\n| --- | --- |\n| T | actual |\n'
        resolver=SourceResolver(raw,'markdown')
        with self.assertRaises(ContractError):resolver.resolve(dict(kind='markdown-cell',heading=['Argument'],row='T',column='Claim'))
        value,_=resolver.resolve(dict(kind='markdown-cell',heading=['Title'],row='T',column='Claim'));self.assertEqual(' actual ',value)
        value=fixture();raw=source_bytes(value['files'][0]['source']).replace(b'Rubric score is not writing quality.','line\u2028separator'.encode())
        value['files'][0]['source']=source_record(raw);value['records'][0]['body']['statement']='line\u2028separator'
        self.assertTrue(self.preview(value)['valid'])

    def test_comments_inside_code_cannot_expose_code_tables_as_ledger_rows(self):
        from claimbranch.core.argument_sources import SourceResolver
        for prefix in (b'```\n<!--\n```\n-->\n',b'Use `<!--` here\n',b'    <!--\n'):
            raw=b'# Argument\n'+prefix+b'```\n| ID | Claim |\n| --- | --- |\n| T | code sample |\n```\n'
            with self.assertRaises(ContractError):SourceResolver(raw,'markdown').resolve(dict(kind='markdown-cell',heading=['Argument'],row='T',column='Claim'))
        value=fixture();value['files'][0]['source']=source_record(source_bytes(value['files'][0]['source']).replace(b'Rubric score is not writing quality.',b'Use `a|b` literally.'))
        value['records'][0]['body']['statement']='Use `a|b` literally.'
        self.assertFalse(self.preview(value)['valid'])

    def test_outer_pipe_less_continuation_cannot_create_a_false_second_table(self):
        from claimbranch.core.argument_sources import SourceResolver
        raw=b'# Argument\n| ID | Claim |\n| --- | --- |\na | b\n| X | Y |\n| --- | --- |\n| T | v |\n'
        with self.assertRaisesRegex(ContractError,'continuation'):
            SourceResolver(raw,'markdown').resolve(dict(kind='markdown-cell',heading=['Argument'],row='T',column='Y'))

    def test_source_silent_assertions_and_scientific_endpoints_are_not_coverage(self):
        value=fixture();result=self.preview(value)
        self.assertGreater(result['coverage']['declared-without-source'],0)
        value['records'][1]['mappings'][0][2]=dict(target='/parent_ids/0',derived='structure-v1')
        self.assertFalse(self.preview(value)['valid'])

    def test_file_digest_mismatch_is_not_covered(self):
        value=fixture();value['files'][0]['source']['sha256']='0'*64
        self.assertFalse(self.preview(value)['valid'])


def paper_fixture():
    """Frozen 430-record/5,400-cell ledger, four originals totaling 1,468,006 bytes."""
    from claimbranch.core.argument_import import _leaves
    from claimbranch.core.argument_import_v2 import _structural
    from .test_typed_observations import TypedObservationTests
    from .test_argument_import import fixture as old_fixture
    metric=deepcopy(old_fixture()['records'][2]['body']['metric'])
    records=[]
    records.append(dict(id='T',kind='thesis',body=dict(statement='Synthetic paper thesis.')))
    for i in range(39):records.append(dict(id=f'C{i}',kind='claim',body=dict(role='main',statement=f'Synthetic claim {i}.',scope='Synthetic prompts',parent_ids=['T'],status='proposed',basis_ids=[])))
    for i in range(41):records.append(dict(id=f'X{i}',kind='experiment',body=dict(question=f'Controlled experiment {i}?',method='Synthetic blind comparison',conditions='Fixed synthetic conditions',metric=metric,source_ref=f'fixture/results-{i}.json')))
    for i in range(100):
        table=TypedObservationTests().table();table['id']=f'table-{i}'
        for row in table['rows']:
            for cell in row['cells']:cell['value']['value']='0.1250'
        records.append(dict(id=f'O{i}',kind='observation',body=dict(experiment_id=f'X{i%41}',statement=f'Synthetic result {i}.',measurement=table,status='confirmed')))
    for i in range(150):records.append(dict(id=f'E{i}',kind='scientific-edge',body=dict(edge_type='supports',source_id=f'O{i%100}',target_id=f'C{i%39}',rationale='The measured synthetic comparison bears on this claim.')))
    for i in range(15):records.append(dict(id=f'P{i}',kind='experiment-plan',body=dict(claim_id=f'C{i}',objective='Test the remaining synthetic limitation.',status='planned',conditions='Fixed future conditions',metric=metric)))
    for i in range(84):records.append(dict(id=f'D{i}',kind='historical-decision',body=dict(group_id=None,rationale='Historical synthetic source decision; not an app approval.',record_ids=[f'C{i%39}',f'O{i%100}'])))
    blobs={key:bytearray() for key in ('claims','results-a','results-b','experiments')}
    for index,record in enumerate(records):
        record['recorded_at']=None
        if index<10:record['origin']=dict(contributor='human',detail='Explicit synthetic exception to the mixed default.')
        key=('results-a' if int(record['id'][1:])<50 else 'results-b') if record['kind']=='observation' else 'claims' if record['kind'] in ('thesis','claim','scientific-edge') else 'experiments'
        blob=blobs[key];blob.extend(f'\n# {record["id"]}\n\n'.encode());mappings=[]
        table=record['body'].get('measurement');cell_targets={}
        if table:
            blob.extend(b'| Cell | direct | mediated | residual |\n| --- | --- | --- | --- |\n')
            for r,row in enumerate(table['rows']):
                blob.extend(('| '+row['id']+' | '+' | '.join(cell['value']['value'] for cell in row['cells'])+' |\n').encode())
                for c,cell in enumerate(row['cells']):cell_targets[f'/measurement/rows/{r}/cells/{c}/value/value']=(row['id'],table['columns'][c]['name'])
            blob.extend(b'\n')
        for target,value in _leaves(record['body']):
            if _structural(target):mappings.append(dict(target=target,derived='structure-v1'));continue
            if target in cell_targets:
                row,column=cell_targets[target]
                locator=dict(kind='markdown-cell',heading=[record['id']],row=row,column=column);normalization='cell-trim-v1';transformation=None
            else:
                blob.extend(('- '+target+': ').encode());start=len(blob)
                rendered=value if isinstance(value,str) else json.dumps(value,separators=(',',':'))
                blob.extend(rendered.encode());end=len(blob);blob.extend(b'\n')
                locator=dict(kind='span',start=start,end=end);normalization='literal-v1'
                transformation=None if isinstance(value,str) else 'Represent the explicitly empty source structure.'
            mappings.append(dict(target=target,file_id=key,locator=locator,normalization=normalization,transformation=transformation))
        record['mappings']=[mappings[i:i+1024] for i in range(0,len(mappings),1024)]
    remaining=1468006-sum(map(len,blobs.values()))
    assert remaining>=0
    prefix=b'\n<!-- Unmapped original limitations retained: ';suffix=b' -->'
    blobs['experiments'].extend(prefix+b'x'*(remaining-len(prefix)-len(suffix))+suffix)
    # Fix padding exactly without changing any mapped byte offset.
    if sum(map(len,blobs.values()))<1468006:blobs['experiments'].extend(b' '*(1468006-sum(map(len,blobs.values()))))
    assert sum(map(len,blobs.values()))==1468006
    vocabulary=[]
    for key,values in [('model',['M1','M2']),('seed',['s1','s2','s3']),('dose',['low','mid','high']),('leg',['primary','sensitivity'])]:
        vocabulary.append(dict(key=key,values=values,groups=[],rationale='Declared synthetic condition taxonomy.'))
    return dict(schema='claimbranch.argument-import/v2',profile='paper',project_id='paper-workload',title='Synthetic lifecycle workload',
        origin_default=dict(contributor='mixed',detail='Synthetic AI-assisted source records.'),condition_vocabulary=vocabulary,
        files=[dict(id=key,name=key+'.md',media='markdown',source=source_record(bytes(blob))) for key,blob in blobs.items()],
        records=records,selected_ids=[record['id'] for record in records])


class OriginalLedgerWorkloadTests(unittest.TestCase):
    def test_representative_original_ledgers_and_typed_cells_preview_deterministically(self):
        value=paper_fixture();raw=encode(value,purpose='project')
        first=preview_import(raw);second=preview_import(raw)
        self.assertTrue(first['valid'],first.get('errors'));self.assertEqual(first,second)
        self.assertEqual(430,len(first['records']));self.assertEqual(1468006,first['source_bytes'])
        self.assertEqual(5400,sum(len(row['cells']) for record in first['records'] if record['kind']=='observation' for row in record['body']['measurement']['rows']))
        self.assertGreater(first['budgets']['expanded_mappings']['used'],8192)
        self.assertEqual(10,sum(record['effective_origin']['contributor']=='human' for record in first['records']))


class OriginalLedgerEntryTests(unittest.TestCase):
    def test_prepare_then_public_preview_from_fresh_source_artifact(self):
        import tempfile,os,subprocess,sys,zipfile
        from pathlib import Path
        from scripts.build_source import build_source
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            root=Path(tmp);sources=root/'paper';sources.mkdir();output=root/'private';output.mkdir(mode=0o700)
            value=fixture();manifest=deepcopy(value);manifest['schema']='claimbranch.argument-source-manifest/v1'
            for file in manifest['files']:
                (sources/file['name']).write_bytes(source_bytes(file.pop('source')));file['path']=file['name']
            path=output/'manifest.json';path.write_bytes(encode(manifest,purpose='project'));path.chmod(0o600)
            archive=root/'source.zip';build_source(archive);extracted=root/'extracted'
            with zipfile.ZipFile(archive) as source:source.extractall(extracted)
            env=dict(os.environ);env.pop('PYTHONPATH',None)
            args=[sys.executable,'-m','claimbranch','project','prepare-import','--manifest',str(path),'--source-root',str(sources),'--output',str(output/'review.json')]
            first=subprocess.run(args,cwd=extracted,env=env,capture_output=True,text=True)
            self.assertEqual(0,first.returncode,first.stderr)
            raw=(output/'review.json').read_bytes();self.assertTrue(preview_import(raw)['valid'])
            duplicate=subprocess.run(args,cwd=extracted,env=env,capture_output=True,text=True)
            self.assertEqual(1,duplicate.returncode);self.assertEqual(raw,(output/'review.json').read_bytes())
            preview=subprocess.run([sys.executable,'-m','claimbranch','project','import-argument','--input',str(output/'review.json'),'--dry-run','--json'],cwd=extracted,env=env,capture_output=True,text=True)
            self.assertEqual(0,preview.returncode,preview.stderr);self.assertTrue(json.loads(preview.stdout)['valid'])
            self.assertEqual(0o600,(output/'review.json').stat().st_mode&0o777)

    def test_preparation_refuses_link_escape_and_invalid_source_before_output(self):
        import tempfile
        from pathlib import Path
        from claimbranch.application.argument_preparation import prepare
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            root=Path(tmp);value=fixture();manifest=deepcopy(value);manifest['schema']='claimbranch.argument-source-manifest/v1'
            file=manifest['files'][0];raw=source_bytes(file.pop('source'));(root/'claims.md').write_bytes(raw);file['path']='claims.md'
            good,_=prepare(encode(manifest,purpose='project'),root);self.assertTrue(preview_import(good)['valid'])
            (root/'link.md').symlink_to(root/'claims.md')
            metadata=root/'.GIT';metadata.mkdir()
            with self.assertRaisesRegex(ContractError,'Git metadata'):prepare(encode(manifest,purpose='project'),metadata)
            for path in ('../claims.md','/claims.md','link.md','./claims.md','.git/config','.GIT/config'):
                file['path']=path
                with self.assertRaises((ContractError,OSError)):prepare(encode(manifest,purpose='project'),root)

    def test_failed_preparation_never_publishes_a_partial_final_name(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        import tempfile,io,os
        from pathlib import Path
        from claimbranch.application.argument_preparation import run_prepare
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            root=Path(tmp);root.chmod(0o700);sources=root/'sources';sources.mkdir();out=root/'private';out.mkdir(mode=0o700)
            value=fixture();value['schema']='claimbranch.argument-source-manifest/v1'
            for file in value['files']:
                raw=source_bytes(file.pop('source'));file['path']=file['name'];(sources/file['path']).write_bytes(raw)
            manifest=out/'manifest.json';manifest.write_bytes(encode(value,purpose='project'));manifest.chmod(0o600)
            args=SimpleNamespace(manifest=manifest,source_root=sources,output=out/'prepared.json',dry_run=False)
            with patch('claimbranch.application.argument_preparation.os.fsync',side_effect=OSError('synthetic disk failure')):
                with self.assertRaises(OSError):run_prepare(args)
            self.assertEqual(['manifest.json'],[file.name for file in out.iterdir()])
            os.link(sources/'claims.md',sources/'alias.md')
            with self.assertRaisesRegex(ContractError,'regular source'):run_prepare(args)

    def test_actual_terminal_can_cancel_v2_preview_without_creating_a_project(self):
        import os,subprocess,sys,tempfile,time,select
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            root=Path(tmp);source=root/'argument.json';source.write_bytes(encode(fixture(),purpose='project'));source.chmod(0o600)
            master,slave=os.openpty();process=subprocess.Popen([sys.executable,'-m','claimbranch','project','import-argument','--input',str(source),'--dry-run'],stdin=slave,stdout=slave,stderr=slave);os.close(slave)
            output=b'';deadline=time.monotonic()+10
            try:
                while b'next page / q' not in output and time.monotonic()<deadline:
                    if select.select([master],[],[],0.2)[0]:output+=os.read(master,16384)
                self.assertIn(b'next page / q',output);os.write(master,b'q\n')
                self.assertEqual(0,process.wait(timeout=5));self.assertEqual(['argument.json'],[file.name for file in root.iterdir()])
            finally:
                if process.poll() is None:process.kill();process.wait()
                os.close(master)


if __name__=='__main__':unittest.main()
