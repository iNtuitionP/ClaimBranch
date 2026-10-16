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


def selector_schema():
    """Separate read-only selector version; old marker contracts are unchanged."""
    return {'type':'object','properties':{'schema':{'const':'claimbranch.tex-selector/v1'},
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
    selector=normalize(selector,selector_schema())
    if type(source) is not bytes or len(source)>2097152:raise ContractError('TeX source exceeds 2 MiB')
    try:text=source.decode('utf-8')

    except UnicodeError:raise ContractError('TeX source must be UTF-8') from None
    if re.search(r'\r(?!\n)',text):raise ContractError('TeX label sources require LF or CRLF lines')
    masked=list(text);i=0
    def blank(a,b):masked[a:b]=' '*(b-a)
    def group(start,left='{',right='}'):
        if start>=len(text) or text[start]!=left:raise ContractError('unsupported TeX argument')
        depth=1;j=start+1
        while j<len(text):
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
                blank(i,end+1);i=end+1;continue
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
                end=body_start+closing.end();blank(i,end);i=end;continue
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
                end=group(j);blank(i,end);i=end;continue
            if re.match(r'\\(?:def|gdef|edef)(?![A-Za-z@])',text[i:]):
                j=text.find('{',i)
                if j<0:raise ContractError('unsupported macro definition')
                end=group(j);blank(i,end);i=end;continue
            i+=2;continue
        i+=1
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
        elif re.match(r'\\(?:if[A-Za-z@]*|else|fi|csname|catcode)(?![A-Za-z@])',value):raise ContractError('conditional or dynamic TeX structure is unsupported')
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
    if selector['kind']=='label' and labels.get(key)!=1:raise ContractError('exact unique literal LaTeX label required')
    chosen=[m for m in matches if m[0]==key and (selector['kind']=='abstract')==(m[3]=='abstract')]
    if len(chosen)!=1:raise ContractError('label is missing, ambiguous or outside supported structure')
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
