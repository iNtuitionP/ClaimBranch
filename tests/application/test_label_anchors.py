"""Literal label spans remain read-only and preserve exact source identities."""
import unittest
from claimbranch.core.canonical import ContractError
from claimbranch.core.marked_text import latex_span


def selector(value,kind='label'):return dict(schema='claimbranch.tex-selector/v1',kind=kind,value=value)


class LabelScannerTests(unittest.TestCase):
    def test_figure_caption_crlf_move_and_section_hierarchy(self):
        figure=b'\\begin{figure*}\r\nData.\\caption{Exact caption.}\\label{fig:test}\r\n\\end{figure*}'
        document=b'\\begin{document}\r\n\\section{First}\\label{sec:first}\r\n'+figure+b'\r\n\\subsection{Child}\\label{sec:child}\r\nchild\r\n\\section{Second}\\label{sec:next}\r\nnext\r\n\\end{document}'
        self.assertEqual(figure,latex_span(document,selector('fig:test')))
        self.assertEqual(figure,latex_span(b'Introduction\r\n'+figure,selector('fig:test')))
        section=latex_span(document,selector('sec:first'))
        self.assertIn(b'Child',section);self.assertNotIn(b'Second',section);self.assertNotIn(b'\\end{document}',latex_span(document,selector('sec:next')))
        self.assertIn(b'child',latex_span(document,selector('sec:child')))

    def test_comments_verbatim_definitions_and_ambiguity(self):
        valid=b'\\begin{figure}\\caption{Result}\\label{fig:x}\\end{figure}'
        ignored=b'% \\label{fig:x}\n\\verb|\\label{fig:x}|\n\\begin{verbatim}\n\\label{fig:x}\n\\end{verbatim}\n\\newcommand{\\example}{\\label{fig:x}}\n'
        self.assertEqual(valid,latex_span(ignored+valid,selector('fig:x')))
        for raw in (valid+valid,b'\\begin{subfigure}\\label{fig:x}\\end{subfigure}',b'\\iftrue'+valid+b'\\fi',b'\\begin{figure}\\label{fig:x}',b'\\section{Title}Body\\label{fig:x}'):
            with self.subTest(raw=raw),self.assertRaises(ContractError):latex_span(raw,selector('fig:x'))

    def test_exact_bounds_and_abstract(self):
        raw=b'\\begin{abstract}\nA bounded summary.\n\\end{abstract}'
        self.assertEqual(raw,latex_span(raw,selector('abstract','abstract')))
        for raw in (b'\\section{Huge}\\label{sec:x}\n'+b'x'*65536,b'x'*2097153):
            with self.assertRaises(ContractError):latex_span(raw,selector('sec:x'))

    def test_spaced_duplicate_inert_code_dynamic_label_and_document_end(self):
        valid=b'\\begin{figure}\\caption{Real}\\label{fig:x}\\end{figure}'
        for raw in (valid+valid.replace(b'\\label{',b'\\label {'),
                    b'\\begin{comment}'+valid+b'\\end{comment}',
                    b'\\begin {comment}'+valid+b'\\end {comment}',
                    b'\\begin {verbatim}'+valid+b'\\end {verbatim}',
                    b'\\begin% comment\n{comment}'+valid+b'\\end{comment}',
                    b'\\begin{figure}\\lstinline!\\label{fig:x}!\\end{figure}',
                    b'\\begin{figure}\\mintinline{tex}{\\label{fig:x}}\\end{figure}',
                    b'\\let\\label\\relax'+valid,
                    b'\\def\\label#1{}'+valid,
                    valid+b'\\label{fi{g}:x}'):
            with self.subTest(raw=raw),self.assertRaises(ContractError):latex_span(raw,selector('fig:x'))
        self.assertEqual(valid,latex_span(valid.replace(b'\\label{',b'\\label {'),selector('fig:x')).replace(b'\\label {',b'\\label{'))
        self.assertEqual(valid,latex_span(b'\\definecolor{red}{rgb}{1,0,0}'+valid,selector('fig:x')))

    def test_spaced_literal_closer_never_exposes_inert_label(self):
        fake=b'\\begin{figure}\\caption{Fake}\\label{fig:x}\\end{figure}\n'
        for name in ('verbatim','verbatim*','Verbatim','comment','lstlisting','minted'):
            raw=('\\begin{'+name+'}\n\\end {'+name+'}\n').encode()+fake+('% \\end{'+name+'}\n').encode()
            with self.subTest(name=name),self.assertRaises(ContractError):latex_span(raw,selector('fig:x'))
            exact=('\\begin {'+name+'}\n').encode()+fake+('\\end{'+name+'}\n').encode()
            with self.subTest(exact=name),self.assertRaises(ContractError):latex_span(exact,selector('fig:x'))

    def test_same_line_literal_closer_and_begin_tail_refuse(self):
        fake=b'\\begin{figure}\\caption{Fake}\\label{fig:x}\\end{figure}\n'
        for name in ('verbatim','verbatim*','Verbatim','comment','lstlisting','minted'):
            raw=('\\begin{'+name+'}\\end{'+name+'}\n').encode()+fake+('%\\end{'+name+'}\n').encode()
            with self.subTest(name=name),self.assertRaises(ContractError):latex_span(raw,selector('fig:x'))

    def test_earlier_midline_closer_cannot_hide_duplicate_and_bare_cr_refuses(self):
        figure=b'\\begin{figure}\\caption{Real}\\label{fig:x}\\end{figure}\n'
        for name in ('verbatim','verbatim*','Verbatim','comment','lstlisting','minted'):
            opening='\\begin{'+name+'}'+('{tex}' if name=='minted' else '')+'\n'
            raw=figure+opening.encode()+('abc\\end{'+name+'}\n').encode()+figure+opening.encode()+('\\end{'+name+'}\n').encode()
            with self.subTest(name=name),self.assertRaises(ContractError):latex_span(raw,selector('fig:x'))
        with self.assertRaises(ContractError):latex_span(figure+b'Bare\rline',selector('fig:x'))

    def test_inline_code_cannot_cross_newline_and_hide_duplicate(self):
        figure=b'\\begin{figure}\\caption{Real}\\label{fig:x}\\end{figure}'
        for opening,closing in ((b'\\verb|a',b'|'),(b'\\lstinline!a',b'!')):
            with self.subTest(opening=opening),self.assertRaises(ContractError):latex_span(figure+opening+b'\n'+figure+closing,selector('fig:x'))


class LabelProjectTests(unittest.TestCase):
    def setUp(self):
        from .test_original_registration import OriginalProjectTests,history,fixture
        from claimbranch.application.project_work import ProjectWork,preview_association
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.core.paper_capacity import encode
        OriginalProjectTests.setUp(self)
        self.raw=b'\\begin{document}\n\\section{Argument}\\label{sec:argument}\nA paper.\n\\begin{figure}\\caption{Independent quality}\\label{fig:quality}\\end{figure}\n\\end{document}\n'
        (self.paper/'paper.tex').write_bytes(self.raw)
        self.preview=preview_association(self.paper,'paper.tex','anchor',self.work,selector=selector('sec:argument'))
        self.project=ProjectWork.create(PaperWork.create(history()),self.preview,import_input=encode(fixture(),purpose='project'))

    def test_label_initial_connection_registration_move_change_missing_return(self):
        from claimbranch.application.manuscript_anchors import prepare_registration,inspect_anchor,recheck_registration
        from claimbranch.application.personal_project import PersonalProjectStore,LABEL_PERSONAL_MAGIC
        from claimbranch.application.personal_archive import split_personal_backup
        from claimbranch.application.project_work import ProjectWork
        from claimbranch.application.paper_service import PaperService
        from claimbranch.core.paper_capacity import decode
        self.assertEqual('claimbranch.project-work/v22',decode(self.project.payload,purpose='project')['schema'])
        project,review=prepare_registration(self.project,manuscript='paper.tex',anchor_id='figure-quality',kind='figure',expresses=['C'],plots=['O'],rationale='Declared quality use.',selector=selector('fig:quality'),contribution_origin='human')
        anchor=project.work.history.view('main')['manuscript_anchors']['figure-quality']
        self.assertEqual(15,decode(project.work.history.commands[-1],purpose='history')['schema_version'])
        self.assertEqual('unchanged',inspect_anchor(anchor)['status']);self.assertEqual(self.raw,(self.paper/'paper.tex').read_bytes())
        self.assertIn('figure-quality',str(PaperService(project.work.history).anchor_impact(['C'])))
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:
            store.save(project,preview=self.preview);returned=split_personal_backup(store.backup())
            self.assertEqual(project.payload,returned.payload)
        self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(LABEL_PERSONAL_MAGIC))
        moved=self.raw.replace(b'A paper.\n',b'A paper.\nNew external text.\n');(self.paper/'paper.tex').write_bytes(moved)
        self.assertEqual('unchanged-block-file-changed',inspect_anchor(anchor)['status'])
        with self.assertRaises(ContractError):recheck_registration(project,review)
        (self.paper/'paper.tex').write_bytes(moved.replace(b'Independent quality',b'Changed quality'))
        self.assertEqual('block-changed',inspect_anchor(anchor)['status'])
        (self.paper/'paper.tex').write_bytes(moved.replace(b'fig:quality',b'fig:deleted'))
        self.assertEqual('unavailable-or-unsupported',inspect_anchor(anchor)['status'])
        self.assertEqual(project.payload,ProjectWork(project.payload).payload)

    def test_public_init_label_dry_run_needs_no_marker_and_refuses_episode(self):
        import io
        from contextlib import redirect_stdout
        from claimbranch.application.cli import main
        args=['project','init','--directory',str(self.work),'--paper-root',str(self.paper),'--manuscript','paper.tex','--label','sec:argument','--title','Synthetic paper','--thesis','Quality needs independent tests.','--question','Does the rubric generalize?','--dry-run']
        output=io.StringIO()
        with redirect_stdout(output):result=main(args+['--profile','paper'])
        self.assertEqual(0,result,output.getvalue());self.assertIn('sec:argument',output.getvalue())
        self.assertFalse((self.work/'personal.cbp').exists());self.assertEqual(self.raw,(self.paper/'paper.tex').read_bytes())
        with redirect_stdout(io.StringIO()):self.assertNotEqual(0,main(args))

    def test_public_label_init_real_terminal_and_source_refresh_preserve_selector(self):
        from .test_tui_terminal import TerminalProcessTests
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.tui_project_source import prepare_source_change
        tty=TerminalProcessTests();tty.setUp();self.addCleanup(tty.tearDown)
        args=['init','--directory',str(self.work),'--paper-root',str(self.paper),'--manuscript','paper.tex','--label','sec:argument','--profile','paper','--title','Synthetic label paper','--thesis','Quality needs blind tests.','--question','What remains untested?']
        tty.launch(personal_arguments=args);tty.expect('Type create');tty.send('create\r','ARGUMENT GRAPH')
        tty.resize(80,24);tty.send('2\x0c','No experiments or observations yet');tty.send('q');tty.assert_restored(0)
        with PersonalProjectStore(self.work) as store:
            project=store.load();self.assertEqual('unchanged',project.source_status())
            (self.paper/'paper.tex').write_bytes(self.raw.replace(b'A paper.',b'A changed external paper.'))
            change=prepare_source_change(project,self.work,'refresh')
            self.assertEqual(selector_v2('sec:argument'),change.project.source_location()['selector'])
            self.assertEqual(project.work.payload,change.project.work.payload)
            store.save(change.project,source_review=change.review)
            self.assertEqual('unchanged-since-refresh',store.load().source_status())
        self.assertIn(b'A changed external paper.',(self.paper/'paper.tex').read_bytes())

    def test_registration_refuses_kind_and_span_mismatch_without_append(self):
        from copy import deepcopy
        from claimbranch.application.manuscript_anchors import prepare_registration
        from claimbranch.core.paper_capacity import decode
        before=self.project.payload
        for kind in ('text','table','caption'):
            with self.subTest(kind=kind),self.assertRaises(ContractError):prepare_registration(self.project,manuscript='paper.tex',anchor_id='figure-quality',kind=kind,selector=selector('fig:quality'),rationale='Must match literal structure.')
        candidate,_=prepare_registration(self.project,manuscript='paper.tex',anchor_id='figure-quality',kind='figure',selector=selector('fig:quality'),rationale='A figure includes its caption.')
        command=decode(candidate.work.history.commands[-1],purpose='history');command['payload']['source']['span_digest']='0'*64
        with self.assertRaises(ContractError):self.project.work.history.append(command)
        self.assertEqual(before,self.project.payload)
        from claimbranch.application.canonical_share import prepare_share,verify_share,SELECTION_SCHEMA
        shared=prepare_share(candidate,dict(schema=SELECTION_SCHEMA,record_ids=['figure-quality'],reason_ids=[]))
        self.assertTrue(verify_share(candidate,shared));self.assertNotIn(b'fig:quality',shared);self.assertNotIn(b'Independent quality',shared)


def selector_v2(value,kind='label'):
    return dict(schema='claimbranch.tex-selector/v2',kind=kind,value=value)


class ConditionalScannerTests(unittest.TestCase):
    figure=b'\\begin{figure}\\caption{Exact caption.}\\label{fig:x}\\end{figure}'

    def test_disjoint_false_archive_switch_and_legacy_refusal(self):
        raw=b'\\newif\\ifRelWork\r\n\\iffalse\r\n{archived, unbalanced \\label{fig:x}\r\n\\fi\r\n'+self.figure+b'\r\n\\ifRelWork\r\nPrior work.\\else Other work.\\fi\r\n'
        self.assertEqual(self.figure,latex_span(raw,selector_v2('fig:x')))
        with self.assertRaisesRegex(ContractError,'conditional'):latex_span(raw,selector('fig:x'))

    def test_inside_enclosing_duplicate_branch_and_malformed_report_line(self):
        cases=[b'\\newif\\ifX\n\\ifX\n'+self.figure+b'\n\\fi',
            b'\\section{Main}\\label{sec:main}\n\\iftrue extra\\fi\n',
            self.figure+b'\n\\iftrue '+self.figure+b'\\fi',
            self.figure+b'\n\\iftrue never closed',self.figure+b'\n\\fi',
            b'\\iftrue {crossing\\fi\n'+self.figure]
        for raw in cases:
            target='sec:main' if raw.startswith(b'\\section') else 'fig:x'
            with self.subTest(raw=raw),self.assertRaisesRegex(ContractError,'conditional at line [12]'):
                latex_span(raw,selector_v2(target))

    def test_comments_code_definitions_and_nested_false_are_inert(self):
        inert=b'% \\iftrue \\fi\n\\verb|\\iftrue|\n\\begin{verbatim}\n\\iftrue\n\\end{verbatim}\n\\newcommand{\\example}{\\iftrue fake \\fi}\n'
        false=b'\\iffalse \\ifnum 1>0 fake \\else ignored \\fi \\fi\n'
        self.assertEqual(self.figure,latex_span(inert+false+self.figure,selector_v2('fig:x')))
        nested=b'\\iftrue \\iffalse {bad \\label{fig:x} \\fi \\fi\n'
        self.assertEqual(self.figure,latex_span(nested+self.figure,selector_v2('fig:x')))
        for raw in (b'\\def\\ifX{}\n'+self.figure,b'\\newif\\ifX\n\\ifX\\newif\\ifY\\fi\n'+self.figure,
                    b'\\ifMystery body\\fi\n'+self.figure,b'\\iffalse\\ifMystery body\\fi\\fi\n'+self.figure,b'\\ifcase 0 a\\else b\\or c\\fi'+self.figure,
                    b'\\catcode 1=2\n'+self.figure):
            with self.subTest(raw=raw),self.assertRaises(ContractError):latex_span(raw,selector_v2('fig:x'))

    def test_unknown_branches_must_not_leak_groups_or_environments(self):
        for prefix in (b'\\iftrue{\\else}\\fi',b'\\iftrue\\begin{figure}\\fi',b'\\iftrue\\end{figure}\\fi'):
            with self.subTest(prefix=prefix),self.assertRaisesRegex(ContractError,'conditional at line'):
                latex_span(prefix+self.figure,selector_v2('fig:x'))
        self.assertEqual(self.figure,latex_span(b'\\ifcase 0 zero\\or one\\else other\\fi'+self.figure,selector_v2('fig:x')))

    def test_false_archive_cannot_forge_a_document_boundary(self):
        raw=b'\\begin{document}\n\\iffalse\\end{document}\\begin{figure}\\label{fig:x}\\fi\n'+self.figure+b'\n\\end{document}'
        self.assertEqual(self.figure,latex_span(raw,selector_v2('fig:x')))
        with self.assertRaises(ContractError):latex_span(b'\\iftrue'*33+b'\\fi'*33+self.figure,selector_v2('fig:x'))

    def test_skipped_branch_literal_masks_cannot_hide_live_duplicate_labels(self):
        for masking in (b'\\verb|\\fi|',b'\\newcommand{\\a}{\\fi}',b'\\def\\a{\\fi}',b'\\begin{verbatim}\n\\fi\n\\end{verbatim}\n'):
            raw=b'\\newif\\ifX\n\\ifX '+masking+self.figure+b'\\fi\n'+self.figure
            with self.subTest(masking=masking),self.assertRaisesRegex(ContractError,'conditional at line 2'):
                latex_span(raw,selector_v2('fig:x'))
        with self.assertRaisesRegex(ContractError,'unknown switch'):
            latex_span(b'\\iffalse\\ifthenelse\\fi'+self.figure+b'\\fi'+self.figure,selector_v2('fig:x'))

    def test_commented_definition_braces_do_not_hide_conditional_duplicates(self):
        raw=b'\\newif\\ifX\n\\newcommand\\a{%{\n}\n\\ifX\n'+self.figure+b'\n\\fi\n}\n'+self.figure
        with self.assertRaises(ContractError):latex_span(raw,selector_v2('fig:x'))
        self.assertEqual(self.figure,latex_span(b'\\newcommand{\\a}{% }\ntext}\n'+self.figure,selector_v2('fig:x')))

    def test_math_iff_is_not_a_conditional_but_redefinition_stays_unsupported(self):
        self.assertEqual(self.figure,latex_span(b'Equation $A\\iff B$.\n'+self.figure,selector_v2('fig:x')))
        self.assertEqual(self.figure,latex_span(b'\\iffalse $A\\iff B$\\fi\n'+self.figure,selector_v2('fig:x')))
        self.assertEqual(self.figure,latex_span(b'\\iftrue $A\\iff B$\\fi\n'+self.figure,selector_v2('fig:x')))
        with self.assertRaises(ContractError):latex_span(b'\\newcommand{\\iff}{fake}'+self.figure,selector_v2('fig:x'))
        with self.assertRaises(ContractError):latex_span(b'\\newif\\iff'+self.figure,selector_v2('fig:x'))


class ConditionalLabelProjectTests(unittest.TestCase):
    setUp=LabelProjectTests.setUp

    def test_versioned_batch_two_labels_and_atomic_failure_preserve_originals(self):
        from claimbranch.application.metadata_batch import prepare_batch,batch_schema
        from claimbranch.application.personal_project import PersonalProjectStore,CONDITIONAL_PERSONAL_MAGIC
        from claimbranch.application.personal_archive import split_personal_backup
        from claimbranch.core.paper_capacity import encode,decode
        from claimbranch.core.research_schema import normalize
        raw=b'\\newif\\ifX\n'+self.raw+b'\n\\iffalse archived abstract\\fi\n'
        (self.paper/'paper.tex').write_bytes(raw)
        from claimbranch.application.project_work import ProjectWork,preview_association
        from .test_original_registration import fixture
        self.preview=preview_association(self.paper,'paper.tex','anchor',self.work,selector=selector_v2('sec:argument'))
        self.project=ProjectWork.create(self.project.work,self.preview,import_input=encode(fixture(),purpose='project'))
        entries=[dict(id='figure-entry',origin='mixed',kind='anchor',request=dict(manuscript='paper.tex',anchor_id='quality-figure',kind='figure',expresses=['C'],plots=['O'],parents=[],rationale='Declare the recorded quality result.',selector=selector_v2('fig:quality'))),
            dict(id='section-entry',origin='unknown',kind='anchor',request=dict(manuscript='paper.tex',anchor_id='argument-section',kind='text',expresses=['C'],plots=[],parents=[],rationale='Declare the argument passage.',selector=selector_v2('sec:argument')))]
        value=dict(schema='claimbranch.metadata-batch/v2',entries=entries,selected_ids=['figure-entry','section-entry'])
        candidate,review=prepare_batch(self.project,encode(value,purpose='project'))
        self.assertTrue(review['valid'],review)
        self.assertEqual('claimbranch.project-work/v24',decode(candidate.payload,purpose='project')['schema'])
        self.assertEqual([17,17],[decode(c,purpose='history')['schema_version'] for c in candidate.work.history.commands[-2:]])
        anchors=candidate.work.history.view('main')['manuscript_anchors'];self.assertEqual(2,len(anchors))
        self.assertEqual('mixed',decode(candidate.work.history.commands[-2],purpose='history')['contribution_origin'])
        with self.assertRaises(ContractError):normalize({**value,'schema':'claimbranch.metadata-batch/v1'},batch_schema(),profile='paper')
        with PersonalProjectStore.create(self.work,project_id=candidate.project_id) as store:
            store.save(candidate,preview=self.preview)
            returned=split_personal_backup(store.backup())
            self.assertEqual(candidate.payload,returned.payload)
        self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(CONDITIONAL_PERSONAL_MAGIC))
        entries[-1]['request']['selector']=selector_v2('missing')
        refused,review=prepare_batch(self.project,encode(value,purpose='project'))
        self.assertIsNone(refused);self.assertFalse(review['valid'])
        self.assertEqual(raw,(self.paper/'paper.tex').read_bytes())

    def test_explicit_connection_upgrade_preserves_work_and_old_binding(self):
        from claimbranch.application.project_work import preview_association,preview_source_refresh
        from claimbranch.core.paper_capacity import decode
        original=decode(self.project.payload,purpose='project')['associations'][0]
        preview=preview_association(self.paper,'paper.tex','anchor',self.work,selector=selector_v2('sec:argument'))
        review=preview_source_refresh(self.project,preview);candidate=self.project.refresh_source(review)
        self.assertEqual(self.project.work.payload,candidate.work.payload)
        self.assertEqual(original,decode(candidate.payload,purpose='project')['associations'][0])
        self.assertEqual(selector_v2('sec:argument'),candidate.source_location()['selector'])
        self.assertEqual('claimbranch.project-work/v24',decode(candidate.payload,purpose='project')['schema'])
        self.assertEqual(self.raw,(self.paper/'paper.tex').read_bytes())

    def test_lint_deduplicates_file_notice_but_keeps_local_unknown_commands(self):
        from claimbranch.application.manuscript_anchors import prepare_registration
        from claimbranch.application.claim_wording import lint
        candidate=self.project
        for key in ('first','second'):
            candidate,_=prepare_registration(candidate,manuscript='paper.tex',anchor_id=key,kind='figure',expresses=['C'],plots=['O'],rationale='Explicit same-span association.',selector=selector_v2('fig:quality'))
        result=lint(candidate.work.history)
        self.assertEqual(1,len(result['notices']))
        self.assertEqual(['first','second'],result['notices'][0]['anchor_ids'])
        self.assertFalse(any(w['code']=='unsupported-tex-semantics' for w in result['warnings']))
        changed=self.raw.replace(b'Independent quality',b'Independent \\mystery quality')
        (self.paper/'paper.tex').write_bytes(changed)
        candidate,_=prepare_registration(self.project,manuscript='paper.tex',anchor_id='unknown-tex',kind='figure',expresses=['C'],rationale='Unknown command remains visible.',selector=selector_v2('fig:quality'))
        self.assertTrue(any(w['code']=='unsupported-tex-semantics' and w['anchor_id']=='unknown-tex' for w in lint(candidate.work.history)['warnings']))

    def test_new_frames_reject_old_prefix_and_read_only_reload_is_identical(self):
        from claimbranch.application.manuscript_anchors import prepare_registration
        from claimbranch.application.personal_project import _PersonalCodec,CONDITIONAL_PERSONAL_MAGIC,SHARED_PERSONAL_MAGIC
        from claimbranch.application.project_work import ProjectWork,project_work_schema
        from claimbranch.core.research_schema import normalize
        from claimbranch.core.paper_capacity import decode
        candidate,_=prepare_registration(self.project,manuscript='paper.tex',anchor_id='new-figure',kind='figure',expresses=['C'],rationale='Declare this use.',selector=selector_v2('fig:quality'))
        codec=_PersonalCodec();frame=codec.seal(candidate.payload)
        self.assertTrue(frame.startswith(CONDITIONAL_PERSONAL_MAGIC))
        self.assertEqual(candidate.payload,codec.open(frame));self.assertEqual(candidate.payload,ProjectWork(candidate.payload).payload)
        with self.assertRaises(ContractError):codec.open(SHARED_PERSONAL_MAGIC+candidate.payload)
        old=decode(candidate.payload,purpose='project');old['schema']='claimbranch.project-work/v23'
        with self.assertRaises(ContractError):normalize(old,project_work_schema(23),profile='paper')

    def test_upgrade_requires_reviewed_save_and_retains_same_label(self):
        from claimbranch.application.project_work import preview_association,preview_source_refresh
        from claimbranch.application.personal_project import PersonalProjectStore
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:
            store.save(self.project,preview=self.preview)
            before=(self.work/'personal.cbp').read_bytes()
            preview=preview_association(self.paper,'paper.tex','anchor',self.work,selector=selector_v2('sec:argument'))
            review=preview_source_refresh(self.project,preview);candidate=self.project.refresh_source(review)
            with self.assertRaises(ContractError):store.save(candidate)
            self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
            store.save(candidate,source_review=review)
            self.assertEqual(candidate.payload,store.load().payload)
        other=preview_association(self.paper,'paper.tex','anchor',self.work,selector=selector_v2('fig:quality'))
        with self.assertRaises(ContractError):preview_source_refresh(self.project,other)


    def test_public_upgrade_cancel_and_confirm_in_real_terminal(self):
        from .test_tui_terminal import TerminalProcessTests
        from claimbranch.application.personal_project import PersonalProjectStore
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:
            store.save(self.project,preview=self.preview)
        original=(self.work/'personal.cbp').read_bytes()
        # A disjoint conditional makes v1 unresolved; only the explicit upgrade fixes it.
        changed=b'\\newif\\ifX\n'+self.raw+b'\n\\ifX Other work.\\fi\n'
        (self.paper/'paper.tex').write_bytes(changed)
        for answer in ('\r','upgrade\r'):
            tty=TerminalProcessTests();tty.setUp()
            try:
                tty.launch(personal_arguments=['upgrade-label-selector','--directory',str(self.work)])
                tty.expect('Type upgrade')
                tty.send(answer)
                import time,select,os,termios
                deadline=time.monotonic()+10
                while tty.process.poll() is None and time.monotonic()<deadline:
                    if select.select([tty.master],[],[],0.05)[0]:tty.output+=os.read(tty.master,65536)
                self.assertEqual(0,tty.process.wait(timeout=5),tty.output[-2000:])
                self.assertEqual(tty.original,termios.tcgetattr(tty.slave))
                self.assertIn(b'\x1b[?2004l',tty.output)
            finally:tty.tearDown()
            if answer=='\r':self.assertEqual(original,(self.work/'personal.cbp').read_bytes())
        with PersonalProjectStore(self.work) as store:
            returned=store.load()
            self.assertEqual(selector_v2('sec:argument'),returned.source_location()['selector'])
            self.assertEqual(self.project.work.payload,returned.work.payload)
            self.assertEqual('unchanged-since-refresh',returned.source_status())
        self.assertEqual(changed,(self.paper/'paper.tex').read_bytes())


    def test_command_selector_discriminators_and_shared_audit_upgrade_roundtrip(self):
        from claimbranch.application.project_commands import prepare_shared_audit
        from claimbranch.application.manuscript_anchors import prepare_registration
        from claimbranch.application.project_work import preview_association,preview_source_refresh
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.personal_archive import split_personal_backup
        from claimbranch.core.paper_capacity import decode
        candidate,_=prepare_registration(self.project,manuscript='paper.tex',anchor_id='v2-figure',kind='figure',expresses=['C'],rationale='Explicit figure use.',selector=selector_v2('fig:quality'))
        cmd=decode(candidate.work.history.commands[-1],purpose='history');cmd['schema_version']=15
        with self.assertRaises(ContractError):self.project.work.history.append(cmd)
        old,_=prepare_registration(self.project,manuscript='paper.tex',anchor_id='v1-figure',kind='figure',expresses=['C'],rationale='Legacy figure use.',selector=selector('fig:quality'))
        cmd=decode(old.work.history.commands[-1],purpose='history');cmd['schema_version']=17
        with self.assertRaises(ContractError):self.project.work.history.append(cmd)
        shared,_=prepare_shared_audit(self.project)
        self.assertEqual('claimbranch.project-work/v23',decode(shared.payload,purpose='project')['schema'])
        preview=preview_association(self.paper,'paper.tex','anchor',self.work,selector=selector_v2('sec:argument'))
        review=preview_source_refresh(shared,preview);upgraded=shared.refresh_source(review)
        self.assertEqual(shared.work.payload,upgraded.work.payload)
        self.assertEqual('claimbranch.project-work/v24',decode(upgraded.payload,purpose='project')['schema'])
        self.assertEqual(selector_v2('sec:argument'),upgraded.source_location()['selector'])
        self.assertEqual('source-refresh',decode(upgraded.payload,purpose='project')['transitions'][-1]['kind'])
        self.assertEqual(decode(shared.payload,purpose='project')['associations'],decode(upgraded.payload,purpose='project')['associations'][:-1])
        with PersonalProjectStore.create(self.work,project_id=shared.project_id) as store:
            store.save(shared,preview=self.preview);store.save(upgraded,source_review=review)
            self.assertEqual(upgraded.payload,split_personal_backup(store.backup()).payload)
