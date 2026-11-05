#!/usr/bin/env python3
"""Static text/path interpretation of historical source edits, never replay jobs.

Only virtual files are touched while interpreting records. Imports, subprocesses,
builds, predictor execution, unknown calls and experiment-result writes are skipped.
"""
import argparse
import ast
import fnmatch
import hashlib
import json
import operator
import pathlib
import posixpath
import re
import shlex
import types

from recover_from_local_records import apply_update, public_candidate, secret_marker, write_json


class Unknown(Exception):
    pass


class Abort(Exception):
    pass


class Returned(Exception):
    def __init__(self, value): self.value=value


class StaticFunction:
    def __init__(self, vm, node, env):self.vm,self.node,self.env=vm,node,env
    def __call__(self,*args,**kwargs):
        env=dict(self.env)
        names=[x.arg for x in self.node.args.args]
        for name,value in zip(names,args):env[name]=value
        env.update(kwargs)
        for name,value in zip(names[-len(self.node.args.defaults):],self.node.args.defaults) if self.node.args.defaults else []:
            if name not in env:env[name]=self.vm.expr(value,env)
        self.vm.depth+=1
        if self.vm.depth>8:self.vm.depth-=1;raise Unknown('FUNCTION_DEPTH')
        try:self.vm.statements(self.node.body,env)
        except Returned as result:return result.value
        finally:self.vm.depth-=1


class VP:
    def __init__(self, vm, value):
        self.vm = vm
        s = str(value)
        self.s = posixpath.normpath(s if s.startswith('/') else vm.cwd + '/' + s)

    def __str__(self): return self.s
    def __truediv__(self, other): return VP(self.vm, self.s + '/' + str(other)) if not str(other).startswith('/') else VP(self.vm, other)
    @property
    def name(self): return posixpath.basename(self.s)
    @property
    def suffix(self): return posixpath.splitext(self.name)[1]
    @property
    def parent(self): return VP(self.vm, posixpath.dirname(self.s))
    @property
    def parents(self):
        out, p = [], self.parent
        while p.s != '/':
            out.append(p);p = p.parent
        return out + [p]
    def resolve(self): return self
    def as_posix(self): return self.s
    def with_name(self,name):return self.parent/name
    def with_suffix(self,suffix):return self.parent/(posixpath.splitext(self.name)[0]+suffix)
    def exists(self): return self.s in self.vm.fs or any(k.startswith(self.s + '/') for k in self.vm.fs)
    def is_file(self): return self.s in self.vm.fs
    def mkdir(self, *args, **kwargs): return None
    def read_text(self, *args, **kwargs):
        if self.s not in self.vm.fs: raise Unknown('MISSING_FILE:' + self.s)
        return self.vm.fs[self.s]
    def read_bytes(self): return self.read_text().encode()
    def write_text(self, text, *args, **kwargs): return self.vm.write(self, text, 'PYTHON_STATIC_TEXT_WRITE')
    def write_bytes(self, data): return self.write_text(data.decode())
    def rglob(self, pattern): return [VP(self.vm, k) for k in sorted(self.vm.fs) if k.startswith(self.s + '/') and fnmatch.fnmatch(posixpath.basename(k), pattern)]
    def glob(self, pattern): return [p for p in self.rglob('*') if fnmatch.fnmatch(p.s[len(self.s) + 1:], pattern)]
    def relative_to(self, other): return pathlib.PurePosixPath(posixpath.relpath(self.s, str(other)))


class VM:
    def __init__(self):
        self.fs, self.meta, self.events = {}, {}, []
        self.cwd = '/home/youns/workspace/ele548-project'
        self.line = 0
        self.depth = 0

    def write(self, path, text, origin):
        s = str(path)
        if not s.startswith('/home/youns/workspace/ele548-project') or not isinstance(text, str): raise Unknown('NON_PROJECT_WRITE')
        p = pathlib.PurePosixPath(s)
        if p.suffix not in ('.py', '.sh', '.cc', '.cpp', '.h', '.hh', '.hpp', '.md', '.txt', '.sv', '.tcl') and p.name not in ('Makefile', 'CMakeLists.txt'): raise Unknown('NOT_SOURCE_TEXT')
        if '/cpu_trials/' in s or len(text) > 2000000: raise Unknown('NOT_SOURCE_TEXT')
        self.fs[s] = text
        self.meta[s] = {'last_source_record_line': self.line, 'derivation': origin}
        return len(text)

    def copy(self, source, dest, tree=False, **kwargs):
        source, dest = VP(self, source), VP(self, dest)
        if tree:
            pairs = [(k, dest.s + k[len(source.s):]) for k in sorted(self.fs) if k.startswith(source.s + '/')]
            if not pairs: raise Unknown('COPYTREE_BASE_MISSING:' + source.s)
        else:
            pairs = [(source.s, dest.s)]
        for old, new in pairs:
            if old not in self.fs: raise Unknown('COPY_BASE_MISSING:' + old)
            self.write(new, self.fs[old], 'VIRTUAL_COPY_FROM:' + old)
        return dest

    def env(self):
        root = VP(self, self.cwd + ('/finite_protection_v18' if not self.cwd.endswith('finite_protection_v18') else ''))
        m = types.SimpleNamespace(BASE=root, B=root, V9=VP(self, '/home/youns/workspace/ele548-project-v9'), V15=VP(self, '/home/youns/workspace/ele548-project-v15/query_controls_v15'))
        path = lambda x='.', *xs: VP(self, posixpath.join(str(x), *map(str, xs)))
        return {'Path':path, 'pathlib':types.SimpleNamespace(Path=path), 'shutil':types.SimpleNamespace(copytree=lambda s,d,**kw:self.copy(s,d,True,**kw), copyfile=self.copy, copy2=self.copy), 'm':m, 'str':str, 'len':len, 'list':list, 'tuple':tuple, 'set':set, 'sorted':sorted, 'enumerate':enumerate, 'range':range, 'int':int, 'print':lambda *a,**k:None, '__name__':'__main__', 're':types.SimpleNamespace(sub=re.sub,escape=re.escape), 'json':types.SimpleNamespace(loads=json.loads,dumps=json.dumps)}

    def expr(self, n, e):
        if isinstance(n, ast.Str): return n.s
        if isinstance(n, ast.Num): return n.n
        if isinstance(n, ast.NameConstant): return n.value
        if hasattr(ast, 'Constant') and isinstance(n, ast.Constant): return n.value
        if isinstance(n, ast.Name):
            if n.id not in e: raise Unknown('UNBOUND:' + n.id)
            return e[n.id]
        if isinstance(n, (ast.List, ast.Tuple, ast.Set)):
            vals = [self.expr(v,e) for v in n.elts]
            return tuple(vals) if isinstance(n,ast.Tuple) else set(vals) if isinstance(n,ast.Set) else vals
        if isinstance(n, ast.Dict): return {self.expr(k,e):self.expr(v,e) for k,v in zip(n.keys,n.values)}
        if isinstance(n, ast.Attribute):
            value = self.expr(n.value,e)
            if n.attr.startswith('_'): raise Unknown('PRIVATE_ATTRIBUTE')
            if value is e.get('Path') and n.attr=='cwd':return lambda:VP(self,self.cwd)
            if value is e.get('Path') and n.attr=='home':return lambda:VP(self,'/home/youns')
            if isinstance(value,types.SimpleNamespace) and n.attr=='Path':return value.Path
            if not isinstance(value,(VP,str,bytes,list,tuple,dict,set,types.SimpleNamespace,pathlib.PurePosixPath)): raise Unknown('UNSUPPORTED_ATTRIBUTE')
            if not hasattr(value,n.attr): raise Unknown('NO_ATTRIBUTE:' + n.attr)
            return getattr(value,n.attr)
        if isinstance(n, ast.Subscript):
            sl=n.slice.value if isinstance(n.slice,ast.Index) else n.slice
            return self.expr(n.value,e)[self.expr(sl,e)]
        if isinstance(n,ast.Slice): return slice(self.expr(n.lower,e) if n.lower else None,self.expr(n.upper,e) if n.upper else None,self.expr(n.step,e) if n.step else None)
        if isinstance(n, ast.BinOp):
            ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Mod:operator.mod}
            if type(n.op) not in ops: raise Unknown('BINOP')
            return ops[type(n.op)](self.expr(n.left,e),self.expr(n.right,e))
        if isinstance(n,ast.UnaryOp):
            value=self.expr(n.operand,e)
            if isinstance(n.op,ast.Not):return not value
            if isinstance(n.op,ast.USub):return -value
            raise Unknown('UNARY')
        if isinstance(n,ast.BoolOp):
            value=self.expr(n.values[0],e)
            for v in n.values[1:]:
                if isinstance(n.op,ast.And) and not value:return value
                if isinstance(n.op,ast.Or) and value:return value
                value=self.expr(v,e)
            return value
        if isinstance(n,ast.Compare):
            funcs={ast.In:lambda a,b:a in b,ast.NotIn:lambda a,b:a not in b,ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Lt:operator.lt,ast.Gt:operator.gt,ast.LtE:operator.le,ast.GtE:operator.ge,ast.Is:operator.is_,ast.IsNot:operator.is_not}
            a=self.expr(n.left,e)
            for op,b in zip(n.ops,n.comparators):
                value=self.expr(b,e)
                if type(op) not in funcs or not funcs[type(op)](a,value):return False
                a=value
            return True
        if isinstance(n,ast.IfExp):return self.expr(n.body if self.expr(n.test,e) else n.orelse,e)
        if isinstance(n,ast.JoinedStr):
            out=''
            for x in n.values:
                if isinstance(x,ast.FormattedValue):out+=format(self.expr(x.value,e),self.expr(x.format_spec,e) if x.format_spec else '')
                else:out+=self.expr(x,e)
            return out
        if isinstance(n,ast.Call):
            # Ignore print without evaluating arguments that might call a job.
            if isinstance(n.func,ast.Name) and n.func.id=='print':return None
            fn=self.expr(n.func,e)
            args=[self.expr(x,e) for x in n.args]
            kwargs={x.arg:self.expr(x.value,e) for x in n.keywords if x.arg}
            if not callable(fn):raise Unknown('NOT_CALLABLE')
            if fn is range and any(abs(int(x))>10000 for x in args):raise Unknown('LOOP_LIMIT')
            return fn(*args,**kwargs)
        raise Unknown('EXPR:' + type(n).__name__)

    def assign(self, node, value, env):
        if isinstance(node,ast.Name):env[node.id]=value
        elif isinstance(node,(ast.Tuple,ast.List)):
            for n,v in zip(node.elts,value):self.assign(n,v,env)
        else:raise Unknown('ASSIGN_TARGET')

    def statements(self, nodes, env):
        for n in nodes:
            try:
                if isinstance(n,ast.Assign):
                    value=self.expr(n.value,env)
                    for t in n.targets:self.assign(t,value,env)
                elif isinstance(n,ast.AugAssign) and isinstance(n.target,ast.Name) and isinstance(n.op,ast.Add):env[n.target.id]+=self.expr(n.value,env)
                elif isinstance(n,ast.Expr):self.expr(n.value,env)
                elif isinstance(n,ast.If):self.statements(n.body if self.expr(n.test,env) else n.orelse,env)
                elif isinstance(n,ast.For):
                    vals=list(self.expr(n.iter,env))
                    if len(vals)>10000:raise Unknown('LOOP_LIMIT')
                    for value in vals:self.assign(n.target,value,env);self.statements(n.body,env)
                elif isinstance(n,ast.Assert):
                    if not self.expr(n.test,env):raise Abort('STATIC_ASSERT_FAILED')
                elif isinstance(n,ast.FunctionDef):env[n.name]=StaticFunction(self,n,env)
                elif isinstance(n,ast.Return):raise Returned(self.expr(n.value,env) if n.value else None)
                # Imports/functions/classes/context managers are never executed.
            except (Unknown,ValueError,TypeError,KeyError,IndexError,AttributeError) as exc:
                # Never let a failed assignment reuse an unrelated old binding.
                if isinstance(n,ast.Assign):
                    for target in n.targets:
                        for name in ast.walk(target):
                            if isinstance(name,ast.Name):env.pop(name.id,None)
                if isinstance(n,ast.For):
                    for name in ast.walk(n.target):
                        if isinstance(name,ast.Name):env.pop(name.id,None)
                self.events.append({'record_line':self.line,'node':type(n).__name__,'reason':str(exc)[:200]})
                if isinstance(n,ast.Assert):raise Abort('STATIC_ASSERT_NOT_VERIFIABLE')


def object_blocks(source):
    for match in re.finditer(r'tools\.exec_command\(\s*\{',source):
        start=source.index('{',match.start());depth=0;quote=None;escape=False
        for i in range(start,len(source)):
            ch=source[i]
            if quote:
                if escape:escape=False
                elif ch=='\\':escape=True
                elif ch==quote:quote=None
                continue
            if ch in ('"',"'",'`'):quote=ch
            elif ch=='{':depth+=1
            elif ch=='}':
                depth-=1
                if depth==0:yield source[start:i+1];break


def prop(block,key):
    m=re.search(r'["\']?'+key+r'["\']?\s*:\s*("(?:\\.|[^"\\])*")',block,re.S)
    if not m:raise Unknown('DYNAMIC_PROPERTY:' + key)
    return json.loads(m.group(1))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--session',type=pathlib.Path,required=True);ap.add_argument('--repo',type=pathlib.Path,required=True);ap.add_argument('--private',type=pathlib.Path,required=True);ap.add_argument('--max-line',type=int,required=True);ap.add_argument('--upstream-seed',type=pathlib.Path);a=ap.parse_args()
    vm=VM();patches=0;heredocs=0;python_blocks=0
    if a.upstream_seed:
        for path in a.upstream_seed.rglob('*'):
            if path.is_file():
                name='/home/youns/workspace/ele548-project-v9/third_party/gem5-native-v9r2/'+path.relative_to(a.upstream_seed).as_posix()
                vm.fs[name]=path.read_text();vm.meta[name]={'last_source_record_line':0,'derivation':'OFFICIAL_PINNED_UPSTREAM_BASE_NOT_DELETED_RESEARCH_FILE'}
    patch_re=re.compile(r'tools\.apply_patch\(\s*("(?:\\.|[^"\\])*")\s*\)',re.S)
    here_re=re.compile(r"(?:^|\n)(cat\s*>\s*([^\n]+?)\s*<<\s*['\"]?(\w+)['\"]?|[^\n]*python[^\n]*<<\s*['\"]?(\w+)['\"]?)\n(.*?)\n(?:\3|\4)(?=\n|$)",re.S)
    with a.session.open() as f:
        for lineno,line in enumerate(f,1):
            if lineno>a.max_line:break
            o=json.loads(line);x=o.get('payload',{})
            if o.get('type')=='turn_context' and isinstance(x,dict) and x.get('cwd'):vm.cwd=x['cwd']
            if o.get('type')!='response_item' or x.get('type')!='custom_tool_call' or x.get('name')!='exec':continue
            vm.line=lineno;source=x.get('input','');actions=[]
            for m in patch_re.finditer(source):actions.append((m.start(),'patch',json.loads(m.group(1))))
            for block in object_blocks(source):
                try:cmd=prop(block,'cmd')
                except Unknown:continue
                try:cwd=prop(block,'workdir')
                except Unknown:cwd=vm.cwd
                actions.append((source.index(block),'command',(cmd,cwd)))
            for _,kind,value in sorted(actions):
                if kind=='patch':
                    patch=value;sections=[]
                    for s in patch.splitlines():
                        m=re.match(r'^\*\*\* (Add|Update|Delete) File: (.+)$',s)
                        if m:sections.append((m.group(1),m.group(2),[]))
                        elif sections and s!='*** End Patch':sections[-1][2].append(s)
                    for operation,name,body in sections:
                        path=VP(vm,name)
                        if not path.s.startswith('/home/youns/workspace/ele548-project'):continue
                        try:
                            if operation=='Add':
                                if any(not x.startswith('+') for x in body):raise Unknown('BAD_ADD')
                                vm.write(path,'\n'.join(x[1:] for x in body)+'\n','RECORDED_ADD_PATCH')
                            elif operation=='Update':vm.write(path,apply_update(path.read_text(),body),'EXACT_CONTEXT_PATCH')
                            else:vm.fs.pop(path.s,None);vm.meta.pop(path.s,None)
                            patches+=1
                        except (Unknown,ValueError) as exc:vm.events.append({'record_line':lineno,'path':path.s,'reason':str(exc)[:200]})
                    continue
                command,cwd=value;original_cwd=vm.cwd;vm.cwd=cwd
                for h in here_re.finditer(command):
                    body=h.group(5)
                    if h.group(2):
                        try:
                            names=shlex.split(h.group(2));assert len(names)==1
                            vm.write(VP(vm,names[0]),body+'\n','SHELL_HEREDOC_LITERAL');heredocs+=1
                        except (Unknown,ValueError,AssertionError):pass
                    else:
                        try:vm.statements(ast.parse(body).body,vm.env());python_blocks+=1
                        except (SyntaxError,Unknown,Abort,Returned):pass
                # Interpret only virtual source-writing semantics of saved scripts.
                for invocation in re.finditer(r'(?:^|\n)(?:[^\s\n]*python[0-9.]*)(?:\s+-[A-Za-z]+)*\s+([^\s<>\n]+\.py)(?=\s|$)',command):
                    script=VP(vm,invocation.group(1))
                    if not script.is_file():continue
                    env=vm.env();env['__file__']=str(script)
                    try:vm.statements(ast.parse(script.read_text()).body,env)
                    except (SyntaxError,Unknown,Abort,Returned):pass
                vm.cwd=original_cwd
    final=[]
    for name,text in sorted(vm.fs.items()):
        rel=name.split('/workspace/',1)[1]
        private=a.private/'static_history_candidates'/rel;private.parent.mkdir(parents=True,exist_ok=True);private.write_text(text)
        if public_candidate(rel) and not secret_marker(text):
            p=a.repo/'recovered_static'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
            final.append({'path':p.relative_to(a.repo).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,**vm.meta[name],'qualification':'STATIC_TEXT_RECOVERY_CANDIDATE_NOT_BUILT_OR_TESTED'})
    write_json(a.repo/'recovery/STATIC_HISTORY_RECOVERY.json',{'static_patch_applications':patches,'literal_heredoc_writes':heredocs,'static_Python_blocks':python_blocks,'candidate_count':len(vm.fs),'public_candidate_count':len(final),'skipped_or_unresolved_operations':len(vm.events),'files':final,'simulations_executed':0,'recorded_commands_executed':False})
    write_json(a.private/'STATIC_UNRESOLVED_OPERATIONS.json',vm.events)
    print(json.dumps({'patches':patches,'heredocs':heredocs,'Python_blocks':python_blocks,'files':len(vm.fs),'public':len(final),'unresolved':len(vm.events)},indent=2))


if __name__=='__main__':main()
