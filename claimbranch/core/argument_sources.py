"""Exact, bounded source locators for personal argument interchange. No file I/O."""
from decimal import Decimal
import hashlib
import re
import unicodedata

from .canonical import ContractError
from .research_schema import ID, TEXT, obj, array

NUMBER = {'type': 'integer', 'minimum': 0, 'maximum': 4194304}
LOCATOR = {'oneOf': [
    obj(kind={'const': 'span'}, start=NUMBER, end=NUMBER),
    obj(kind={'const': 'lines'}, start={'type': 'integer', 'minimum': 1, 'maximum': 4194304},
        end={'type': 'integer', 'minimum': 1, 'maximum': 4194304}),
    obj(kind={'const': 'json-pointer'}, pointer={'type': 'string', 'minLength': 0, 'maxLength': 2048}),
    obj(kind={'const': 'markdown-cell'}, heading=array(TEXT, 8), row=TEXT, column=TEXT),
]}
NORMALIZATIONS = ['literal-v1', 'cell-trim-v1', 'prose-nfc-v1']


def text(raw):
    try:
        return raw.decode('utf-8')
    except UnicodeError as error:
        raise ContractError('Source must be exact UTF-8 text') from error


def _span(raw, start, end):
    if not 0 <= start <= end <= len(raw):
        raise ContractError('Source span is outside the retained file')
    if end-start > 16384:
        raise ContractError('Source extraction exceeds 16384 bytes; select a smaller explicit span')
    # Reject boundaries inside multibyte UTF-8 characters.
    if (start < len(raw) and raw[start] & 0xc0 == 0x80) or (end < len(raw) and raw[end] & 0xc0 == 0x80):
        raise ContractError("Source span splits a UTF-8 character")
    value = text(raw[start:end])
    return value, dict(start=start, end=end)


def _cells(line):
    """GFM splits unescaped pipes before parsing inline code; retain literal bytes."""
    content=line.rstrip('\r\n');delimiters=[];cursor=0
    while cursor<len(content):
        if content[cursor]=='\\':cursor+=2;continue
        if content[cursor]=='|':delimiters.append(cursor)
        cursor+=1
    if len(delimiters)<2 or content[:delimiters[0]].strip() or content[delimiters[-1]+1:].strip():
        raise ContractError('Markdown cell selector requires explicit outer pipes')
    return [(a+1,b) for a,b in zip(delimiters,delimiters[1:])]


def _markdown_index(raw, budget):
    """One linear scan, bounded cell index and O(1) positive/negative lookups."""
    if b'\r' in raw.replace(b'\r\n',b''):raise ContractError('Bare-CR Markdown is unsupported; use explicit source spans')
    parts=raw.split(b'\n');lines=[text(part).rstrip('\r') for part in parts]
    offsets=[];offset=0
    for part in parts:offsets.append(offset);offset+=len(part)+1
    headings=[];occurrences={():1};cells={};errors={};fence=None;comment=False;i=0
    def enter(rank,title):
        while headings and headings[-1][0]>=rank:headings.pop()
        headings.append((rank,title));path=tuple(title for _,title in headings)
        occurrences[path]=occurrences.get(path,0)+1
    def store(path,row,column,span):
        key=(path,row,column)
        # Two are sufficient to preserve ambiguity without unbounded duplicate lists.
        matches=cells.setdefault(key,[])
        if len(matches)<2:matches.append(span)
        budget['markdown_cells']=budget.get('markdown_cells',0)+1
        if budget['markdown_cells']>131072:raise ContractError('capacity indexed-markdown-cells: exceeds 131072')
    while i<len(lines):
        line=lines[i];path=tuple(title for _,title in headings)
        marker=re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$',line)
        if fence:
            if marker and marker[1][0]==fence[0] and len(marker[1])>=len(fence) and not marker[2].strip():fence=None
            i+=1;continue
        if comment:
            if '-->' in line:comment=False
            i+=1;continue
        if line.startswith(('    ','\t')):i+=1;continue
        if marker and not (marker[1][0]=='`' and '`' in marker[2]):
            fence=marker[1];i+=1;continue
        if re.match(r'^ {0,3}<!--',line):
            comment='-->' not in line.split('<!--',1)[1];i+=1;continue
        heading=re.match(r'^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*$',line)
        if heading:
            enter(len(heading[1]),re.sub(r'[ \t]+#+[ \t]*$','',heading[2]));i+=1;continue
        if line.strip() and not line.lstrip().startswith(('|','>')) and i+1<len(lines) and re.fullmatch(r' {0,3}(=+|-+)[ \t]*',lines[i+1]):
            enter(1 if lines[i+1].lstrip().startswith('=') else 2,line.strip());i+=2;continue
        if not line.lstrip().startswith('|') or i+1>=len(lines):i+=1;continue
        try:
            header=_cells(line);separator=_cells(lines[i+1])
            if not all(re.fullmatch(r'\s*:?-{3,}:?\s*',lines[i+1][a:b]) for a,b in separator):i+=1;continue
            names=[line[a:b].strip(' \t') for a,b in header]
            if len(names)!=len(separator) or len(names)!=len(set(names)) or len(names)>128:
                raise ContractError('Unsupported or ambiguous Markdown table columns')
            i+=2
            while i<len(lines) and lines[i].lstrip().startswith('|') and not lines[i].startswith(('    ','\t')):
                row=lines[i];spans=_cells(row)
                if len(spans)!=len(names):raise ContractError('Unsupported irregular Markdown row')
                row_key=row[spans[0][0]:spans[0][1]].strip(' \t')
                for column,(a,b) in zip(names,spans):
                    start=offsets[i]+len(row[:a].encode('utf-8'));end=offsets[i]+len(row[:b].encode('utf-8'))
                    store(path,row_key,column,(start,end))
                i+=1
            if i<len(lines) and lines[i].strip() and not re.match(r'^ {0,3}(?:#{1,6}(?:[ \t]|$)|`{3,}|~{3,}|>|<!--|[-+*][ \t]|[0-9]+[.)][ \t])',lines[i]):
                errors[path]='Unsupported Markdown table continuation; use an explicit source span'
        except ContractError as error:
            if 'capacity ' in str(error):raise
            errors[path]=str(error);i+=1
    return occurrences,cells,errors


class SourceResolver:
    """One bounded read-only resolver/cache per retained file and preview."""
    def __init__(self, raw, media, budget=None):
        text(raw)
        self.raw=raw;self.media=media;self.markdown=None;self.markdown_error=None;self.json=None;self.json_error=None;self.lines=None
        self.budget=budget if budget is not None else {}

    def resolve(self, locator):
        from .research_schema import _check
        _check(locator, LOCATOR)
        raw,media=self.raw,self.media
        kind=locator['kind']
        if kind=='json-pointer':
            if media!='json':raise ContractError('JSON pointers require a JSON source')
            if self.json_error:raise ContractError(self.json_error)
            if self.json is None:
                import json
                from .argument_import import _leaves
                def pairs(items):
                    result={};seen=set()
                    for key,value in items:
                        normalized=unicodedata.normalize('NFC',key)
                        if normalized in seen:raise ContractError('Duplicate normalized source JSON key')
                        seen.add(normalized);result[key]=value
                    return result
                def reject(_):raise ContractError('Nonfinite source JSON number')
                try:
                    parsed=json.loads(text(raw),object_pairs_hook=pairs,parse_float=Decimal,parse_constant=reject)
                    leaves={}
                    for pointer,value in _leaves(parsed):
                        self.budget['json_leaves']=self.budget.get('json_leaves',0)+1
                        self.budget['json_pointer_bytes']=self.budget.get('json_pointer_bytes',0)+len(pointer.encode('utf-8'))
                        if self.budget['json_leaves']>65536 or self.budget['json_pointer_bytes']>8388608:
                            raise ContractError('capacity indexed-json-leaves/pointer-bytes: exceeds 65536 / 8388608')
                        leaves[pointer]=value
                    self.json=leaves
                except (ValueError,RecursionError,ContractError) as error:
                    self.json_error=str(error);raise ContractError(self.json_error) from error
            if locator['pointer'] not in self.json:raise ContractError('JSON pointer has no scalar leaf')
            value=self.json[locator['pointer']]
            if isinstance(value,(dict,list)) and value:raise ContractError('JSON source mappings require scalar or empty-container leaves')
            if isinstance(value,str) and len(value.encode('utf-8'))>16384:raise ContractError('Source extraction exceeds 16384 bytes')
            return value,{'pointer':locator['pointer']}
        if kind=='markdown-cell':
            if media!='markdown':raise ContractError('Markdown cells require a Markdown source')
            if self.markdown_error:raise ContractError(self.markdown_error)
            if self.markdown is None:
                try:self.markdown=_markdown_index(raw,self.budget)
                except ContractError as error:
                    self.markdown_error=str(error);raise
            occurrences,cells,errors=self.markdown;path=tuple(locator['heading'])
            if occurrences.get(path,0)!=1:raise ContractError('Markdown heading path is absent or ambiguous')
            if path in errors:raise ContractError(errors[path])
            spans=cells.get((path,locator['row'],locator['column']),[])
            if len(spans)!=1:raise ContractError('Markdown row/column is absent or ambiguous')
            return _span(raw,*spans[0])
        if kind=='lines':
            if self.lines is None:
                # Only LF is a line separator; CRLF bytes are retained inside each line.
                self.lines=[0]
                self.lines.extend(index+1 for index,ch in enumerate(raw) if ch==10)
                if self.lines[-1]!=len(raw):self.lines.append(len(raw))
            offsets=self.lines
            if not 1<=locator['start']<=locator['end']<len(offsets):
                raise ContractError('Source line range is outside the retained file')
            return _span(raw,offsets[locator['start']-1],offsets[locator['end']])
        return _span(raw,locator['start'],locator['end'])


def resolve(raw,media,locator):
    return SourceResolver(raw,media).resolve(locator)


def normalized(value, policy, locator):
    if policy == 'literal-v1': return value
    if not isinstance(value, str): raise ContractError('Text normalization requires text')
    if policy == 'cell-trim-v1':
        if locator['kind'] != 'markdown-cell': raise ContractError('Cell trim requires a Markdown cell')
        return value.strip(' \t')
    if policy == 'prose-nfc-v1':
        if any(token in value for token in ('`', '$', '\\')):
            raise ContractError('Prose normalization refuses code/math; use a literal span')
        return unicodedata.normalize('NFC', value)
    raise ContractError('Unknown source normalization version')
