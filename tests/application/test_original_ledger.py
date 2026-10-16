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
                while b'Review: details / q' not in output and time.monotonic()<deadline:
                    if select.select([master],[],[],0.2)[0]:output+=os.read(master,16384)
                self.assertIn(b'Review: details / q',output);os.write(master,b'q\n')
                self.assertEqual(0,process.wait(timeout=5));self.assertEqual(['argument.json'],[file.name for file in root.iterdir()])
            finally:
                if process.poll() is None:process.kill();process.wait()
                os.close(master)




class SourceV3Tests(unittest.TestCase):
    def mapped(self, raw, expected, policy, locator=None, media='json'):
        value=fixture();value['schema']='claimbranch.argument-import/v3'
        value['records']=value['records'][:1];value['selected_ids']=['T']
        value['files'][0].update(media=media,source=source_record(raw))
        record=value['records'][0];record['body']['statement']=expected
        record['mappings'][0][0].update(locator=locator or dict(kind='json-pointer',pointer='/x'),normalization=policy)
        return value

    def test_json_decimal_bridge_preserves_precision_sign_and_exponent(self):
        cases=[('0.0108','0.0108',True),('1e-3','0.001',True),('1.230','1.230',True),
            ('1.230','1.23',False),('1.0e3','1000',False),('-0','-0',True),('-0','0',False),
            ('-0.00','-0.00',True),('-0.00','0.00',False),('true','1',False)]
        for number,target,valid in cases:
            with self.subTest(number=number,target=target):
                value=self.mapped(('{"x":'+number+'}').encode(),target,'json-number-decimal-v1')
                result=preview_import(encode(value,purpose='project'))
                self.assertEqual(valid,result['valid'],result.get('errors'))
                if valid:self.assertEqual('normalized-exact',result['records'][0]['coverage'][0]['state'])

    def test_boolean_policy_is_separate_and_explicit(self):
        for source,target,valid in [('true','true',True),('false','false',True),('true','True',False),('1','true',False)]:
            with self.subTest(source=source,target=target):
                value=self.mapped(('{"x":'+source+'}').encode(),target,'json-boolean-text-v1')
                self.assertEqual(valid,preview_import(encode(value,purpose='project'))['valid'])

    def test_signed_numeric_grouping_is_narrow_and_precision_is_retained(self):
        for source,target,valid in [('−0.668','-0.668',True),('+0.668','0.668',True),
            ('1\u2009234.50','1234.50',True),('−1\u202f234.50','-1234.50',True),
            ('1 234.50','1234.50',False),('12\u200934.50','1234.50',False),
            ('−0.668','0.668',False),('−0.668','-0.67',False),('1.230','1.23',False)]:
            with self.subTest(source=source,target=target):
                raw=source.encode();value=self.mapped(raw,target,'numeric-sign-v1',dict(kind='span',start=0,end=len(raw)),media='text')
                self.assertEqual(valid,preview_import(encode(value,purpose='project'))['valid'])

    def test_line_trim_removes_exactly_one_terminal_newline_only_for_lines(self):
        for raw,target,end,valid in [(b'hello\r\n','hello',1,True),(b'hello\n','hello',1,True),
            (b'hello\n\n','hello',2,False),(b'hello \n','hello',1,False)]:
            value=self.mapped(raw,target,'line-trim-v1',dict(kind='lines',start=1,end=end),media='text')
            self.assertEqual(valid,preview_import(encode(value,purpose='project'))['valid'])
        value=self.mapped(b'hello\n','hello','line-trim-v1',dict(kind='span',start=0,end=6),media='text')
        self.assertFalse(preview_import(encode(value,purpose='project'))['valid'])

    def test_markdown_section_occurrences_and_exact_crlf_span(self):
        raw='# Log\r\n## Decision\r\n첫 판단\r\n### Detail\r\nreason\r\n## Decision\r\nsecond\r\n# End\r\n'.encode()
        locator=dict(kind='markdown-section',heading=['Log','Decision'],occurrence=1)
        expected='## Decision\r\n첫 판단\r\n### Detail\r\nreason\r\n'
        value=self.mapped(raw,expected,'literal-v1',locator,media='markdown')
        result=preview_import(encode(value,purpose='project'));self.assertTrue(result['valid'],result.get('errors'))
        coverage=result['records'][0]['coverage'][0]
        self.assertEqual(expected.encode(),raw[coverage['resolved']['start']:coverage['resolved']['end']])
        self.assertEqual('exact',coverage['state']);self.assertEqual('mixed',result['records'][0]['effective_origin']['contributor'])
        value['records'][0]['mappings'][0][0]['locator'].pop('occurrence')
        self.assertFalse(preview_import(encode(value,purpose='project'))['valid'])

    def test_old_v2_contract_stays_closed(self):
        value=self.mapped(b'{"x":0.0108}','0.0108','json-number-decimal-v1')
        value['schema']='claimbranch.argument-import/v2'
        self.assertFalse(preview_import(encode(value,purpose='project'))['valid'])

    def test_markdown_sections_ignore_fenced_indented_and_commented_headings(self):
        from claimbranch.core.argument_sources import SourceResolver
        raw=b'# Log\nStart\n```md\n# Fake\n```\n    # Code\n<!--\n# Hidden\n-->\nChild\n-----\nbody\n# End\n'
        resolver=SourceResolver(raw,'markdown',version=2)
        selected,span=resolver.resolve(dict(kind='markdown-section',heading=['Log']))
        self.assertEqual(raw[:raw.index(b'# End')].decode(),selected)
        self.assertEqual(0,span['start'])
        child,_=resolver.resolve(dict(kind='markdown-section',heading=['Log','Child']))
        self.assertEqual('Child\n-----\nbody\n',child)
        for heading in (['Fake'],['Hidden'],['Log','Code']):
            with self.assertRaises(ContractError):resolver.resolve(dict(kind='markdown-section',heading=heading))

    def test_new_section_and_cell_share_one_bounded_index(self):
        from unittest.mock import patch
        from claimbranch.core import argument_sources as sources
        raw=source_bytes(fixture()['files'][0]['source'])
        for section_first in (False,True):
            with patch.object(sources,'_markdown_index',wraps=sources._markdown_index) as scan:
                resolver=sources.SourceResolver(raw,'markdown',version=2)
                locators=[dict(kind='markdown-section',heading=['Argument']),dict(kind='markdown-cell',heading=['Argument'],row='T',column='Claim')]
                for locator in locators if section_first else reversed(locators):resolver.resolve(locator)
                self.assertEqual(1,scan.call_count)

    def test_sections_are_byte_bound_and_changed_snapshot_changes_commitment(self):
        value=self.mapped(b'# Only\nBody\n','# Only\nBody\n','literal-v1',dict(kind='markdown-section',heading=['Only']),media='markdown')
        first=preview_import(encode(value,purpose='project'));self.assertTrue(first['valid'])
        value['files'][0]['source']=source_record(b'# Only\nDifferent\n')
        self.assertFalse(preview_import(encode(value,purpose='project'))['valid'])
        value['records'][0]['body']['statement']='# Only\nDifferent\n'
        second=preview_import(encode(value,purpose='project'));self.assertTrue(second['valid'])
        self.assertNotEqual(first['preview_digest'],second['preview_digest'])
        value['files'][0]['source']=source_record(b'# Only\n'+b'x'*16384)
        self.assertFalse(preview_import(encode(value,purpose='project'))['valid'])

    def test_decimal_expansion_and_invalid_exponents_fail_bounded(self):
        for number in ('1e-20000','1e99999999999999999999999'):
            value=self.mapped(('{"x":'+number+'}').encode(),'1','json-number-decimal-v1')
            result=preview_import(encode(value,purpose='project'));self.assertFalse(result['valid'])
            self.assertTrue(result['errors'])

    def test_precision_loss_can_only_be_a_declared_transformation(self):
        value=self.mapped(b'{"x":1.230}','1.23','json-number-decimal-v1')
        value['records'][0]['mappings'][0][0]['transformation']='Source precision deliberately reduced for this display.'
        result=preview_import(encode(value,purpose='project'));self.assertTrue(result['valid'],result.get('errors'))
        coverage=result['records'][0]['coverage'][0]
        self.assertEqual('transformed',coverage['state']);self.assertEqual('1.230',coverage['normalized'])
        self.assertEqual({'source_decimal':'1.230'},coverage['original'])

    def test_multiline_setext_is_refused_in_new_resolver_without_changing_old_cells(self):
        from claimbranch.core.argument_sources import SourceResolver
        raw=b'# Log\nFirst title line\nSecond title line\n---\nbody\n'
        with self.assertRaisesRegex(ContractError,'setext'):
            SourceResolver(raw,'markdown',version=2).resolve(dict(kind='markdown-section',heading=['Log']))
        # Old resolver retains its literal table indexing behavior.
        table=b'| ID | Claim |\n| --- | --- |\n| T | Old cell |\n'
        selected,_=SourceResolver(raw+table,'markdown').resolve(dict(kind='markdown-cell',heading=['Log','Second title line'],row='T',column='Claim'))
        self.assertEqual(' Old cell ',selected)

    def test_empty_atx_heading_ends_a_section_in_new_resolver(self):
        from claimbranch.core.argument_sources import SourceResolver
        raw=b'# Log\nBody\n#\nOther text\n'
        value,_=SourceResolver(raw,'markdown',version=2).resolve(dict(kind='markdown-section',heading=['Log']))
        self.assertEqual('# Log\nBody\n',value)

    def test_v2_preview_commitment_is_unchanged(self):
        result=preview_import(encode(fixture(),purpose='project'))
        self.assertEqual('eacd0762861fac80894af42be15bcd7251f24fc13dfbc15c5f918c4aef753c7f',result['preview_digest'])

    def test_canonical_exponent_rendering_retains_tuple_in_text_but_cannot_claim_expansion(self):
        value=self.mapped(b'{"x":1.0e3}','1.0E+3','json-number-decimal-v1')
        result=preview_import(encode(value,purpose='project'));self.assertTrue(result['valid'])
        coverage=result['records'][0]['coverage'][0]
        self.assertEqual('normalized-exact',coverage['state'])
        self.assertEqual({'source_decimal':'1.0E+3'},coverage['original'])
        value['records'][0]['body']['statement']='1000'
        self.assertFalse(preview_import(encode(value,purpose='project'))['valid'])

    def test_ambiguous_markdown_continuations_do_not_invent_sections(self):
        from claimbranch.core.argument_sources import SourceResolver
        cases=[b'| not a table\nTitle\n---\nbody\n',b'para\n    more\nTitle\n---\n',
            b'- item\n---\n',b'1. item\n---\n',b'> quote\nTitle\n---\n',b'- item\nTitle\n---\n',
            b'| standalone pipe\n---\n',b'<div>\n# Hidden\n</div>\n']
        for body in cases:
            with self.subTest(body=body),self.assertRaisesRegex(ContractError,'span locator'):
                SourceResolver(b'# Log\n'+body,'markdown',version=2).resolve(dict(kind='markdown-section',heading=['Log']))

    def test_hash_only_atx_and_thematic_breaks_do_not_invent_named_sections(self):
        from claimbranch.core.argument_sources import SourceResolver
        for empty in (b'## ##',b'## ###',b'# #'):
            resolver=SourceResolver(b'# Log\nBody\n'+empty+b'\nOther\n','markdown',version=2)
            with self.subTest(empty=empty),self.assertRaises(ContractError):
                resolver.resolve(dict(kind='markdown-section',heading=['Log','##']))
        raw=b'# Log\nBody\n\n---\n---\nAfter\n'
        selected,_=SourceResolver(raw,'markdown',version=2).resolve(dict(kind='markdown-section',heading=['Log']))
        self.assertEqual(raw.decode(),selected)

    def test_new_cell_resolver_refuses_ambiguous_setext_while_v1_keeps_old_path(self):
        from claimbranch.core.argument_sources import SourceResolver
        raw=b'# Log\nFirst\nSecond\n---\n| ID | Claim |\n| --- | --- |\n| T | Cell |\n'
        locator=dict(kind='markdown-cell',heading=['Log','Second'],row='T',column='Claim')
        self.assertEqual(' Cell ',SourceResolver(raw,'markdown').resolve(locator)[0])
        with self.assertRaisesRegex(ContractError,'setext'):SourceResolver(raw,'markdown',version=2).resolve(locator)

    def test_signed_markdown_cell_trims_only_its_declared_boundaries(self):
        raw='# Results\n| ID | Value |\n| --- | --- |\n| O | −1\u202f234.50 |\n'.encode()
        value=self.mapped(raw,'-1234.50','numeric-sign-v1',dict(kind='markdown-cell',heading=['Results'],row='O',column='Value'),media='markdown')
        result=preview_import(encode(value,purpose='project'));self.assertTrue(result['valid'],result.get('errors'))
        self.assertEqual('normalized-exact',result['records'][0]['coverage'][0]['state'])

    def test_v2_locator_stays_closed_even_with_legacy_policy(self):
        value=self.mapped(b'# Only\nBody\n','# Only\nBody\n','literal-v1',dict(kind='markdown-section',heading=['Only']),media='markdown')
        value['schema']='claimbranch.argument-import/v2'
        self.assertFalse(preview_import(encode(value,purpose='project'))['valid'])


class HistoricalImportV4Tests(unittest.TestCase):
    def fixture(self):
        value=fixture();value['schema']='claimbranch.argument-import/v4';value['structural_defaults']=['claim','experiment','observation','historical-decision']
        value['records'][1]['mappings'][0]=[m for m in value['records'][1]['mappings'][0] if m['target']!='/basis_ids']
        return value

    def preview(self,value):return preview_import(encode(value,purpose='project'))

    def test_only_declared_bookkeeping_defaults_avoid_repeated_maps(self):
        result=self.preview(self.fixture());self.assertTrue(result['valid'],result.get('errors'))
        coverage=result['records'][1]['coverage'];self.assertIn(dict(target='/basis_ids',state='structural-default'),coverage)
        value=self.fixture();value['records'][1]['mappings'][0]=[m for m in value['records'][1]['mappings'][0] if m['target']!='/scope']
        self.assertFalse(self.preview(value)['valid'])

    def test_sourceless_new_input_has_own_origin_and_no_dummy_file(self):
        value=self.fixture();record=value['records'][1]
        record['mappings'][0][0]=dict(target='/statement',source_silent=True,origin=dict(contributor='ai',detail='New suggestion.'),transformation='New wording, not copied from the ledger.')
        record['joint_origin']=dict(contributor='mixed',detail='Ledger and new suggestion.')
        result=self.preview(value);self.assertTrue(result['valid'],result.get('errors'))
        coverage=result['records'][1]['coverage'][0];self.assertEqual('declared-without-source',coverage['state']);self.assertNotIn('file_id',coverage)
        self.assertTrue(result['records'][1]['effective_origin']['ai'])
        record['origin']=dict(contributor='human',detail='Present confirming actor.')
        self.assertTrue(self.preview(value)['records'][1]['effective_origin']['ai'])

    def test_incomplete_experiment_original_label_and_day_precision_survive_replay(self):
        from claimbranch.core.argument_import import history_from_import
        value=self.fixture();value['files'].append(dict(id='experiment',name='experiment.md',media='text',source=source_record(b'What explains the gap?')))
        value['records'].append(dict(id='expA ModelB',kind='experiment',body=dict(question='What explains the gap?'),recorded_at='2026-10-12',display_label='expA ModelB',mappings=[[dict(target='/question',file_id='experiment',locator=dict(kind='span',start=0,end=22),normalization='literal-v1',transformation=None)]]))
        value['selected_ids'].append('expA ModelB')
        result=self.preview(value);self.assertTrue(result['valid'],result.get('errors'))
        history=history_from_import(encode(value,purpose='project'),anchor_id='anchor')
        run=history.view('main')['experiments'][0]
        self.assertIsNone(run['metric']);self.assertIsNone(run['method']);self.assertIn('/metric',run['not_recorded'])
        self.assertEqual('expA ModelB',run['display_label'])
        self.assertEqual('2026-10-12',run['recorded_at'])
        self.assertEqual(history.manifest(),type(history)(history.seed,history.commands).manifest())

    def test_invalid_day_and_original_identity_collisions_are_refused(self):
        value=self.fixture();value['records'][0]['recorded_at']='2026-02-31'
        self.assertFalse(self.preview(value)['valid'])
        value=self.fixture();value['records'][1]['display_label']='T'
        self.assertFalse(self.preview(value)['valid'])

    def test_independent_unspecified_origin_stays_unknown_beside_known_ai(self):
        value=self.fixture();record=value['records'][1]
        record['mappings'][0][0]=dict(target='/statement',source_silent=True,transformation='New wording of uncertain authorship.')
        result=self.preview(value);self.assertTrue(result['valid'],result.get('errors'))
        flags=result['records'][1]['effective_origin'];self.assertTrue(flags['ai']);self.assertTrue(flags['unknown'])

    def test_display_aliases_cannot_name_another_record_even_with_its_own_label(self):
        value=self.fixture();value['records'][0]['display_label']='C';value['records'][1]['display_label']='Other'
        self.assertFalse(self.preview(value)['valid'])

    def test_independent_only_record_cannot_drop_source_or_joint_assertions(self):
        value=self.fixture();value['records']=value['records'][:1];value['selected_ids']=['T']
        record=value['records'][0];record['mappings']=[[dict(target='/statement',source_silent=True,origin=dict(contributor='ai',detail=None),transformation='Proposed working thesis.')]]
        record['source_origins']=[dict(file_id='ledger',origin=dict(contributor='ai',detail=None))]
        self.assertFalse(self.preview(value)['valid']);record.pop('source_origins')
        record['joint_origin']=dict(contributor='human',detail='Cannot erase the declared AI.')
        self.assertFalse(self.preview(value)['valid'])
        record['joint_origin']['contributor']='mixed'
        result=self.preview(value);self.assertTrue(result['valid'],result.get('errors'))
        self.assertTrue(result['records'][0]['effective_origin']['ai'])

    def test_file_origin_is_a_replaceable_default_but_independent_ai_is_not(self):
        value=self.fixture();value['files'][0]['origin_default']=dict(contributor='ai',detail='File default, with explicit record exceptions.')
        value['records'][0]['origin']=dict(contributor='human',detail='This particular statement was written by the researcher.')
        result=self.preview(value);self.assertTrue(result['valid'],result.get('errors'))
        self.assertFalse(result['records'][0]['effective_origin']['ai'])

    def test_joint_human_label_cannot_override_independent_ai_with_file_inputs(self):
        value=self.fixture();value['origin_default']=dict(contributor='human',detail=None)
        record=value['records'][1];record['joint_origin']=dict(contributor='human',detail='Inconsistent joint assertion.')
        record['mappings'][0][0]=dict(target='/statement',source_silent=True,origin=dict(contributor='ai',detail=None),transformation='New proposed wording.')
        self.assertFalse(self.preview(value)['valid'])


if __name__=='__main__':unittest.main()


class PreparationIterationTests(unittest.TestCase):
    def setUp(self):
        import tempfile,sys
        from pathlib import Path
        self.tmp=tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform=='darwin' else None);self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.output=self.root/'prepared.json';self.value=fixture();self.raw=encode(self.value,purpose='project')

    def test_replace_requires_exact_reviewed_identity_and_keeps_old_on_failure(self):
        import hashlib
        from claimbranch.application.argument_preparation import publish_prepared
        publish_prepared(self.raw,self.output,protected=[])
        old=self.output.read_bytes();digest=hashlib.sha256(old).hexdigest()
        changed=deepcopy(self.value);changed['title']='New synthetic preparation';raw=encode(changed,purpose='project')
        with self.assertRaises(ContractError):publish_prepared(raw,self.output,protected=[])
        with self.assertRaises(ContractError):publish_prepared(raw,self.output,protected=[],expected_sha256='0'*64)
        from unittest.mock import patch
        with patch('claimbranch.application.argument_preparation.os.replace',side_effect=OSError('replace refused')):
            with self.assertRaises(OSError):publish_prepared(raw,self.output,protected=[],expected_sha256=digest)
        self.assertEqual(old,self.output.read_bytes())
        publish_prepared(raw,self.output,protected=[],expected_sha256=digest);self.assertEqual(raw,self.output.read_bytes())

    def test_originals_unrecognized_files_links_and_second_save_as_collision_are_refused(self):
        from claimbranch.application.argument_preparation import publish_prepared
        import hashlib,os
        self.output.write_bytes(self.raw);self.output.chmod(0o600);digest=hashlib.sha256(self.raw).hexdigest()
        with self.assertRaises(ContractError):publish_prepared(self.raw,self.output,protected=[self.output],expected_sha256=digest)
        self.output.write_bytes(b'original ledger');digest=hashlib.sha256(self.output.read_bytes()).hexdigest()
        with self.assertRaises(ContractError):publish_prepared(self.raw,self.output,protected=[],expected_sha256=digest)
        valid=self.root/'valid.json';valid.write_bytes(self.raw);valid.chmod(0o600)
        other=self.root/'alias.json';os.symlink(valid,other)
        with self.assertRaises((ContractError,OSError)):publish_prepared(self.raw,other,protected=[],expected_sha256=digest)
        new=self.root/'new.json';publish_prepared(self.raw,new,protected=[])
        with self.assertRaises(ContractError):publish_prepared(self.raw,new,protected=[])
        self.assertEqual(b'original ledger',self.output.read_bytes())


    def test_world_readable_valid_envelope_and_concurrent_edit_are_refused(self):
        from claimbranch.application.argument_preparation import publish_prepared
        import hashlib
        publish_prepared(self.raw,self.output,protected=[]);digest=hashlib.sha256(self.raw).hexdigest();self.output.chmod(0o644)
        with self.assertRaises(ContractError):publish_prepared(self.raw,self.output,protected=[],expected_sha256=digest)
        self.output.chmod(0o600)
        def change():self.output.write_bytes(b'changed outside preparation')
        with self.assertRaises(ContractError):publish_prepared(self.raw,self.output,protected=[],expected_sha256=digest,recheck=change)
        self.assertEqual(b'changed outside preparation',self.output.read_bytes())

    def test_published_cleanup_failure_reports_uncertainty_and_closes_directory(self):
        from claimbranch.application.argument_preparation import publish_prepared
        from unittest.mock import patch
        import os
        real_close=os.close;real_open=os.open;directory_fds=[]
        def opened(path,flags,*args,**kwargs):
            fd=real_open(path,flags,*args,**kwargs)
            if path==self.root and flags&os.O_DIRECTORY:directory_fds.append(fd)
            return fd
        with patch('claimbranch.application.argument_preparation.os.open',side_effect=opened),patch('claimbranch.application.argument_preparation.os.unlink',side_effect=OSError('cleanup refused')),patch('claimbranch.application.argument_preparation.os.close',wraps=real_close) as close:
            with self.assertRaisesRegex(ContractError,'may be published; cleanup is uncertain'):
                publish_prepared(self.raw,self.output,protected=[])
            descriptors=[call.args[0] for call in close.call_args_list]
        self.assertEqual(self.raw,self.output.read_bytes())
        self.assertTrue(directory_fds)
        for fd in directory_fds:
            self.assertIn(fd,descriptors)
            with self.assertRaises(OSError):os.fstat(fd)

    def test_failed_initial_temp_identity_closes_fd_and_names_uncertain_temp(self):
        from claimbranch.application.argument_preparation import publish_prepared
        from unittest.mock import patch
        import os
        opened=[];real_open=os.open;real_fstat=os.fstat
        def opening(path,*args,**kwargs):
            fd=real_open(path,*args,**kwargs)
            if str(path).startswith('.argument-prepare-'):opened.append(fd)
            return fd
        def fstat(fd):
            if fd in opened:raise OSError('identity read refused')
            return real_fstat(fd)
        with patch('claimbranch.application.argument_preparation.os.open',side_effect=opening),patch('claimbranch.application.argument_preparation.os.fstat',side_effect=fstat):
            with self.assertRaisesRegex(ContractError,'temporary cleanup is uncertain: .argument-prepare-'):
                publish_prepared(self.raw,self.output,protected=[])
        self.assertFalse(self.output.exists());self.assertEqual(1,len(opened))
        with self.assertRaises(OSError):real_fstat(opened[0])

    def test_cleanup_failure_does_not_hide_primary_unpublished_failure(self):
        from claimbranch.application.argument_preparation import publish_prepared
        from unittest.mock import patch
        def refuse():raise ContractError('Source changed; prepare again')
        with patch('claimbranch.application.argument_preparation.os.unlink',side_effect=OSError('cleanup refused')):
            with self.assertRaisesRegex(ContractError,'Source changed; prepare again') as caught:
                publish_prepared(self.raw,self.output,protected=[],recheck=refuse)
        self.assertIn('Temporary cleanup is uncertain',caught.exception.__notes__[0]);self.assertFalse(self.output.exists())

    def test_flush_failure_preserves_old_and_postpublication_failure_is_uncertain(self):
        from claimbranch.application.argument_preparation import publish_prepared
        from unittest.mock import patch
        import hashlib,os
        publish_prepared(self.raw,self.output,protected=[])
        old=self.output.read_bytes();digest=hashlib.sha256(old).hexdigest()
        changed=deepcopy(self.value);changed['title']='New preparation';raw=encode(changed,purpose='project')
        with patch('claimbranch.application.argument_preparation.os.fsync',side_effect=OSError('flush refused')):
            with self.assertRaises(OSError):publish_prepared(raw,self.output,protected=[],expected_sha256=digest)
        self.assertEqual(old,self.output.read_bytes())
        real_fsync=os.fsync
        def sync(fd):
            import stat
            if stat.S_ISDIR(os.fstat(fd).st_mode):raise OSError('directory sync refused')
            return real_fsync(fd)
        with patch('claimbranch.application.argument_preparation.os.fsync',side_effect=sync):
            with self.assertRaisesRegex(ContractError,'may be published'):
                publish_prepared(raw,self.output,protected=[],expected_sha256=digest)
        self.assertEqual(raw,self.output.read_bytes())
