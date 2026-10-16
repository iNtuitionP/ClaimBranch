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
            self.assertEqual(selector('sec:argument'),change.project.source_location()['selector'])
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
