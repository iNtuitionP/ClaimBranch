"""Pure replacement of one exact LF-delimited marker block; never a writer."""
import hashlib

from .canonical import ContractError, bounded_text, digest_text, identifier


def tex_text(text):
    escapes = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "&": r"\&",
               "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
               "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(escapes.get(char, char) for char in text)


def preview_marked_text(source, marker, text, expected_digest):
    identifier(marker)
    bounded_text(text)
    digest_text(expected_digest)
    if type(source) is not bytes or len(source) > 65536 or hashlib.sha256(source).hexdigest() != expected_digest:
        raise ContractError("marked source changed or exceeds the fixture bound")
    start = f"% claimbranch:start id={marker}\n".encode()
    end = f"% claimbranch:end id={marker}\n".encode()
    lines = source.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line == start]
    ends = [index for index, line in enumerate(lines) if line == end]
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ContractError("exact unique ordered LF markers required")
    return b"".join(lines[:starts[0] + 1]) + tex_text(text).encode("utf-8") + b"\n" + b"".join(lines[ends[0]:])


def marked_block(source, marker):
    """Read a unique explicitly named block; no include expansion or writing."""
    identifier(marker)
    if type(source) is not bytes or len(source)>2097152:
        raise ContractError('marked source exceeds 2 MiB')
    source.decode('utf-8')
    lines=source.splitlines(keepends=True)
    starts=[i for i,line in enumerate(lines) if line==f'% claimbranch:start id={marker}\n'.encode()]
    ends=[i for i,line in enumerate(lines) if line==f'% claimbranch:end id={marker}\n'.encode()]
    if len(starts)!=1 or len(ends)!=1 or starts[0]>=ends[0]:
        raise ContractError('exact unique ordered LF markers required')
    raw=b''.join(lines[starts[0]+1:ends[0]])
    if len(raw)>65536: raise ContractError('marked block exceeds 64 KiB')
    return raw


def selector_schema(version=1):
    """Separate read-only selector version; old marker contracts are unchanged."""
    if version not in (1,2): raise ContractError('Unknown TeX selector version')
    return {'type':'object','properties':{'schema':{'const':f'claimbranch.tex-selector/v{version}'},
        'kind':{'enum':['label','abstract']},'value':{'type':'string','minLength':1,'maxLength':160,'pattern':r'^[A-Za-z0-9:._/-]+$'}},
        'required':['schema','kind','value'],'additionalProperties':False}


def selected_block(source, marker, selector=None):
    return marked_block(source,marker) if selector is None else latex_span(source,selector)


def latex_span(source, selector):
    """Bounded literal TeX scanner, not TeX execution or general macro expansion.

    Labels must be outside braces in figure/table[*], or immediately after a
    standard sectioning command. Comments, verbatim, inline verb and common
    macro definitions are excluded; unresolved structure refuses, never guesses.
    """
    import re
    from .research_schema import normalize
    version = 2 if type(selector) is dict and selector.get('schema') == 'claimbranch.tex-selector/v2' else 1
    selector=normalize(selector,selector_schema(version))
    if type(source) is not bytes or len(source)>2097152:raise ContractError('TeX source exceeds 2 MiB')
    try:text=source.decode('utf-8')

    except UnicodeError:raise ContractError('TeX source must be UTF-8') from None
    if re.search(r'\r(?!\n)',text):raise ContractError('TeX label sources require LF or CRLF lines')
    masked=list(text);i=0
    condition_stack=[]; regions=[]; declared=set()
    primitives={'if','ifcat','ifnum','ifdim','ifodd','ifvmode','ifhmode','ifmmode','ifinner','ifvoid','ifhbox','ifvbox','ifx','ifeof','iftrue','iffalse','ifcase','ifdefined','ifcsname','iffontchar'}
    from bisect import bisect_right
    from array import array
    newlines=array('I',(j for j,char in enumerate(text) if char=='\n')) if version==2 else ()
    def at_line(pos): return bisect_right(newlines,pos)+1
    def conditional_error(pos, reason):
        raise ContractError('TeX conditional at line %s: %s' % (at_line(pos),reason))
    def blank(a,b):masked[a:b]=' '*(b-a)
    def check_mask(a,b):
        if version==2 and condition_stack and any(m[1]!='iff' for m in re.finditer(r'\\(if[A-Za-z@]*|else|or|fi)(?![A-Za-z@])',text[a:b])):
            conditional_error(condition_stack[0]['start'],'literal code or macro masks a possible branch terminator')
    def group(start,left='{',right='}'):
        if start>=len(text) or text[start]!=left:raise ContractError('unsupported TeX argument')
        depth=1;j=start+1
        while j<len(text):
            if version==2 and text[j]=='%':
                newline=text.find('\n',j);j=len(text) if newline<0 else newline+1;continue
            if text[j]=='\\':j+=2;continue
            if text[j]==left:depth+=1
            elif text[j]==right:
                depth-=1
                if not depth:return j+1
            j+=1
        raise ContractError('unterminated TeX argument')
    while i<len(text):
        if text[i]=='%':
            end=text.find('\n',i);end=len(text) if end<0 else end
            blank(i,end);i=end;continue
        if text[i]=='\\':
            if version == 2:
                declaration=re.match(r'\\newif(?![A-Za-z@])\s*(\\if[A-Za-z@]+)(?![A-Za-z@])',text[i:])
                if declaration and not any(frame['false'] for frame in condition_stack):
                    name=declaration[1][1:]
                    if name in primitives|{'iff'} or name in declared:conditional_error(i,'ambiguous switch declaration')
                    if condition_stack:conditional_error(i,'switch declaration in an uncertain branch')
                    declared.add(name);end=i+declaration.end();blank(i,end);i=end;continue
                conditional=re.match(r'\\(if[A-Za-z@]*|else|or|fi)(?![A-Za-z@])',text[i:])
                if conditional and conditional[1]!='iff':
                    name=conditional[1]
                    if name.startswith('if'):
                        if name not in primitives|declared:
                            conditional_error(i,'unknown switch; a literal newif declaration is required')
                        if len(condition_stack)>=32:conditional_error(i,'nesting exceeds 32')
                        condition_stack.append(dict(start=i,false=name=='iffalse',else_seen=False,name=name))
                    elif not condition_stack:conditional_error(i,'unmatched '+name)
                    elif name in ('else','or'):
                        frame=condition_stack[-1]
                        if frame['else_seen'] or (name=='or' and frame['name']!='ifcase'):conditional_error(i,'ambiguous '+name)
                        if name=='else':frame['else_seen']=True
                        # A false condition with else has an active alternative;
                        # never treat that whole region as an inert comment.
                        if name=='else':frame['false']=False
                    else:
                        frame=condition_stack.pop()
                        inert=frame['name']=='iffalse' and not frame['else_seen']
                        if not condition_stack:
                            if len(regions)>=2048:conditional_error(i,'region count exceeds 2048')
                            regions.append((frame['start'],i+conditional.end(),inert))
                        elif inert:blank(frame['start'],i+conditional.end())
                    i+=conditional.end();continue
                if any(frame['false'] for frame in condition_stack):
                    i+=2;continue
            verb=re.match(r'\\(?:verb|lstinline)\*?([^A-Za-z\s{])',text[i:])
            env=re.match(r'\\begin\s*\{(verbatim\*?|Verbatim|lstlisting|minted|comment)\}',text[i:])
            definition=re.match(r'\\(?:newcommand|renewcommand|providecommand|DeclareRobustCommand)\*?',text[i:])
            if re.match(r'\\(?:lstinline|mintinline)(?![A-Za-z@])',text[i:]) and not verb:raise ContractError('unsupported inline-code syntax')
            if re.match(r'\\(?:let|expandafter|futurelet|catcode|csname)(?![A-Za-z@])',text[i:]):raise ContractError('dynamic TeX structure is unsupported')
            if re.match(r'\\(?:newcommand|renewcommand|providecommand|DeclareRobustCommand)\*?\s*\{?\\(?:label|begin|end|section|subsection)(?![A-Za-z@])',text[i:]):raise ContractError('structural TeX command redefinition is unsupported')
            if re.match(r'\\(?:def|gdef|edef)\s*\\(?:label|begin|end|section|subsection)(?![A-Za-z@])',text[i:]):raise ContractError('structural TeX command redefinition is unsupported')
            if verb:
                a=i+verb.end();end=text.find(verb[1],a);newline=text.find('\n',a)
                if end<0 or 0<=newline<end:raise ContractError('unterminated inline verbatim')
                check_mask(i,end+1);blank(i,end+1);i=end+1;continue
            if env:
                # Begin-line tails are not literal-environment body lines.
                # Support only ordinary options/language followed by whitespace.
                line_end=text.find('\n',i+env.end())
                if line_end<0:raise ContractError('literal environment needs a body line')
                j=i+env.end()
                while j<line_end and text[j] in ' \t\r':j+=1
                if env[1] in ('Verbatim','lstlisting','minted') and j<line_end and text[j]=='[':j=group(j,'[',']')
                while j<line_end and text[j] in ' \t\r':j+=1
                if env[1]=='minted':j=group(j)
                if j>line_end or text[j:line_end].strip():raise ContractError('unsupported literal environment opening-line tail')
                body_start=line_end+1
                # Supported literal environments close on an exact standalone
                # line. A spaced end command remains inert body text.
                prefix='' if env[1]=='comment' else '[ \t]*'
                closing=re.search(r'^'+prefix+r'\\end\{'+re.escape(env[1])+r'\}[ \t]*\r?$',text[body_start:],re.MULTILINE)
                if closing is None:raise ContractError('unterminated verbatim environment')
                first=re.search(r'\\end\s*\{'+re.escape(env[1])+r'\}',text[body_start:])
                token_start=closing.start()+len(closing.group())-len(closing.group().lstrip(' \t'))
                if first is None or first.start()!=token_start or first.group()!='\\end{'+env[1]+'}':raise ContractError('ambiguous literal environment closer')
                end=body_start+closing.end();check_mask(i,end);blank(i,end);i=end;continue
            if version==2 and re.match(r'\\(?:def|gdef|edef|newcommand|renewcommand|providecommand)\*?\s*\{?\\(?:if[A-Za-z@]*|else|fi|or|newif)(?![A-Za-z@])',text[i:]):raise ContractError('conditional TeX command redefinition is unsupported')
            if definition:
                j=i+definition.end()
                while j<len(text) and text[j].isspace():j+=1
                if j<len(text) and text[j]=='{':j=group(j)
                else:
                    name=re.match(r'\\[A-Za-z@]+',text[j:])
                    if not name:raise ContractError('unsupported macro definition')
                    j+=name.end()
                while j<len(text):
                    while j<len(text) and text[j].isspace():j+=1
                    if j<len(text) and text[j]=='[':j=group(j,'[',']')
                    else:break
                end=group(j);check_mask(i,end);blank(i,end);i=end;continue
            if re.match(r'\\(?:def|gdef|edef)(?![A-Za-z@])',text[i:]):
                j=text.find('{',i)
                if j<0:raise ContractError('unsupported macro definition')
                end=group(j);check_mask(i,end);blank(i,end);i=end;continue
            i+=2;continue
        i+=1
    if condition_stack:conditional_error(condition_stack[0]['start'],'unterminated region')
    conditional_labels=[]
    if version == 2:
        for start,end,inert in regions:
            region=''.join(masked[start:end])
            if not inert:
                _validate_conditional_region(region,at_line(start))
                if selector['kind']=='label' and re.search(r'\\label(?![A-Za-z@])\s*\{'+re.escape(selector['value'])+r'\}',region):
                    conditional_labels.append(start)
            blank(start,end)
    clean=''.join(masked)
    tokens=re.compile(r'\\(?:begin|end)\s*\{([A-Za-z*]+)\}|\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)(?![A-Za-z])\*?|\\label(?![A-Za-z])\s*\{([^{}]+)\}|\\[A-Za-z@]+|\\.|[{}]')
    stack=[];sections=[];matches=[];labels={};depth=0;skip=0;document_end=len(text)
    ranks={name:n for n,name in enumerate(('part','chapter','section','subsection','subsubsection','paragraph','subparagraph'))}
    for token in tokens.finditer(clean):
        if token.start()<skip:continue
        value=token.group();pos=token.start()
        if token[1]:
            name=token[1]
            if name in ('verbatim','verbatim*','Verbatim','lstlisting','minted','comment'):raise ContractError('unsupported unmasked literal environment')
            if value.startswith('\\begin'):
                entry=dict(name=name,start=pos,labels=[],depth=depth);stack.append(entry)
            else:
                if not stack or stack[-1]['name']!=name:raise ContractError('ambiguous TeX environment nesting')
                entry=stack.pop()
                if name=='document':
                    document_end=token.start();break
                for label in entry['labels']:matches.append((label,entry['start'],token.end(),name))
                if selector['kind']=='abstract' and name=='abstract':matches.append(('abstract',entry['start'],token.end(),name))
        elif token[2]:
            if depth or any(e['name']!='document' for e in stack):raise ContractError('unsupported nested sectioning command')
            j=token.end()
            while j<len(clean) and clean[j].isspace():j+=1
            if j<len(clean) and clean[j]=='[':j=group(j,'[',']')
            while j<len(clean) and clean[j].isspace():j+=1
            end=group(j);skip=end
            sections.append(dict(rank=ranks[token[2]],start=pos,title_end=end,labels=[]))
        elif token[3]:
            label=token[3];labels[label]=labels.get(label,0)+1
            if depth:continue
            if any(e['name']!='document' for e in stack):
                if stack[-1]['name'] in ('figure','figure*','table','table*') and not any(e['name'] in ('figure','figure*','table','table*') for e in stack[:-1]):stack[-1]['labels'].append(label)
            elif sections and not clean[sections[-1]['title_end']:pos].strip():sections[-1]['labels'].append(label)
        elif value in ('\\label','\\begin','\\end'):raise ContractError('unsupported literal structural command argument')
        elif (version==1 or value!='\\iff') and re.match(r'\\(?:if[A-Za-z@]*|else|fi|csname|catcode)(?![A-Za-z@])',value):raise ContractError('conditional or dynamic TeX structure is unsupported')
        elif value=='{':depth+=1
        elif value=='}':
            depth-=1
            if depth<0:raise ContractError('unbalanced TeX group')
    if depth or stack:raise ContractError('unterminated TeX group/environment')
    for n,section in enumerate(sections):
        end=next((s['start'] for s in sections[n+1:] if s['rank']<=section['rank']),document_end)
        for label in section['labels']:matches.append((label,section['start'],end,'section'))
    key=selector['value']
    if selector['kind']=='abstract' and key!='abstract':raise ContractError('abstract selector must name abstract')
    if conditional_labels:conditional_error(conditional_labels[0],'selected label may lie in a conditional branch')
    if selector['kind']=='label' and labels.get(key)!=1:raise ContractError('exact unique literal LaTeX label required')
    chosen=[m for m in matches if m[0]==key and (selector['kind']=='abstract')==(m[3]=='abstract')]
    if len(chosen)!=1:raise ContractError('label is missing, ambiguous or outside supported structure')
    for start,end,inert in regions:
        if start < chosen[0][2] and end > chosen[0][1]:conditional_error(start,'conditional overlaps or is enclosed by the selected span')
    raw=text[chosen[0][1]:chosen[0][2]].encode('utf-8')
    if len(raw)>65536:raise ContractError('resolved TeX span exceeds 64 KiB')
    return raw


def validate_span_kind(raw, kind):
    """A label selects an entire environment, never an inferred caption slice."""
    import re
    if kind=='caption':raise ContractError('Caption-only anchors require explicit marker blocks')
    match=re.match(rb'\\begin\s*\{(figure\*?|table\*?)\}',raw)
    actual=match[1].rstrip(b'*').decode() if match else 'text'
    if kind!=actual:raise ContractError('Anchor kind differs from the literal label structure')


def _validate_conditional_region(text, first_line):
    """Each possible branch must be structurally self-contained, never executed."""
    import re
    structural=[];frames=[]
    token=re.compile(r'\\(?:begin|end)\s*\{([A-Za-z*]+)\}|\\(if[A-Za-z@]*|else|or|fi)(?![A-Za-z@])|\\[A-Za-z@]+|\\.|[{}]')
    for match in token.finditer(text):
        value=match.group()
        def refuse():
            raise ContractError('TeX conditional at line %s: branch structure crosses conditional boundaries' % (first_line+text.count('\n',0,match.start())))
        if match[2] and match[2]!='iff':
            name=match[2]
            if name.startswith('if'):frames.append(tuple(structural))
            elif name in ('else','or'):
                if not frames or tuple(structural)!=frames[-1]:refuse()
            else:
                if not frames or tuple(structural)!=frames.pop():refuse()
        elif match[1]:
            if value.startswith('\\begin'):structural.append(('env',match[1]))
            elif not structural or structural.pop()!=('env',match[1]):refuse()
        elif value=='{':structural.append(('group',None))
        elif value=='}':
            if not structural or structural.pop()!=('group',None):refuse()
    if structural or frames:raise ContractError('TeX conditional at line %s: incomplete branch structure' % first_line)
