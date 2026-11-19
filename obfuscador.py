#!/usr/bin/env python3
# obfuscator.py — Luau VM obfuscator
# CFF + math-code + silent anti-logger + anti-tamper v3 + new anti-env
import re, random, argparse, base64

# ─── Lexer ──────────────────────────────────────────────────────────────────
TOKEN_RE = re.compile(r'''
    (?P<WS>\s+)
  | (?P<COMMENT>--\[\[.*?\]\]|--[^\n]*)
  | (?P<STRING>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
  | (?P<NUMBER>\d+\.\d+|\d+)
  | (?P<NAME>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<OP>==|~=|<=|>=|\.\.|[-+*/%^#<>=(){}\[\];:,\.])
''', re.VERBOSE | re.DOTALL)
KEYWORDS = {'local','if','then','else','elseif','end','while','do','for','in',
            'function','return','true','false','nil','and','or','not',
            'repeat','until','break'}

class Token:
    __slots__=('t','v')
    def __init__(s,t,v): s.t=t; s.v=v
    def __repr__(s): return f'Token({s.t},{s.v!r})'

def lex(src):
    toks,pos=[],0
    while pos<len(src):
        m=TOKEN_RE.match(src,pos)
        if not m: raise SyntaxError(f'Bad char at {pos}')
        kind,val=m.lastgroup,m.group(); pos=m.end()
        if kind in ('WS','COMMENT'): continue
        if kind=='NAME' and val in KEYWORDS: toks.append(Token('KW',val))
        elif kind=='STRING': toks.append(Token('STRING',val[1:-1]))
        elif kind=='NUMBER': toks.append(Token('NUMBER',float(val) if '.' in val else int(val)))
        elif kind=='NAME': toks.append(Token('NAME',val))
        else: toks.append(Token('OP',val))
    toks.append(Token('EOF','<eof>'))
    return toks

# ─── AST ────────────────────────────────────────────────────────────────────
class Node: pass
class Num(Node):
    def __init__(s,v): s.v=v
class Str(Node):
    def __init__(s,v): s.v=v
class Bool(Node):
    def __init__(s,v): s.v=v
class Nil(Node): pass
class Name(Node):
    def __init__(s,n): s.n=n
class BinOp(Node):
    def __init__(s,op,l,r): s.op,s.l,s.r=op,l,r
class UnOp(Node):
    def __init__(s,op,e): s.op,s.e=op,e
class Call(Node):
    def __init__(s,fn,args): s.fn,s.args=fn,args
class Assign(Node):
    def __init__(s,names,vals): s.names,s.vals=names,vals
class Local(Node):
    def __init__(s,names,vals): s.names,s.vals=names,vals
class If(Node):
    def __init__(s,c,b,o): s.cond,s.body,s.orelse=c,b,o
class While(Node):
    def __init__(s,c,b): s.cond,s.body=c,b
class Block(Node):
    def __init__(s,stmts): s.stmts=stmts
class Return(Node):
    def __init__(s,exprs): s.exprs=exprs

class Parser:
    def __init__(s,toks): s.toks=toks; s.i=0
    def peek(s): return s.toks[s.i]
    def eat(s,t=None,v=None):
        tok=s.toks[s.i]
        if t and tok.t!=t: raise SyntaxError(f'Expected {t}, got {tok}')
        if v and tok.v!=v: raise SyntaxError(f'Expected {v!r}, got {tok}')
        s.i+=1; return tok
    def accept(s,t=None,v=None):
        tok=s.toks[s.i]
        if t and tok.t!=t: return None
        if v and tok.v!=v: return None
        s.i+=1; return tok
    def parse(s):
        stmts=[]
        while s.peek().t!='EOF':
            st=s.stmt()
            if st: stmts.append(st)
        return Block(stmts)
    def stmt(s):
        t=s.peek()
        if t.t=='KW' and t.v=='local': return s.local_stmt()
        if t.t=='KW' and t.v=='if': return s.if_stmt()
        if t.t=='KW' and t.v=='while': return s.while_stmt()
        if t.t=='KW' and t.v=='return':
            s.eat(); exprs=[]
            if s.peek().t!='EOF' and s.peek().v!='end':
                exprs.append(s.expr())
                while s.accept(t='OP',v=','): exprs.append(s.expr())
            return Return(exprs)
        if t.t=='NAME':
            save=s.i; name=s.eat('NAME').v
            if s.accept(t='OP',v='='):
                vals=[s.expr()]
                while s.accept(t='OP',v=','): vals.append(s.expr())
                return Assign([name],vals)
            s.i=save
        return s.expr()
    def local_stmt(s):
        s.eat('KW','local')
        names=[s.eat('NAME').v]
        while s.accept(t='OP',v=','): names.append(s.eat('NAME').v)
        vals=[]
        if s.accept(t='OP',v='='):
            vals=[s.expr()]
            while s.accept(t='OP',v=','): vals.append(s.expr())
        return Local(names,vals)
    def if_stmt(s):
        s.eat('KW','if'); cond=s.expr(); s.eat('KW','then')
        body=[]
        while s.peek().t!='EOF' and not (s.peek().t=='KW' and s.peek().v in ('end','else','elseif')):
            st=s.stmt()
            if st: body.append(st)
        orelse=[]
        if s.accept(t='KW',v='else'):
            while s.peek().t!='EOF' and not (s.peek().t=='KW' and s.peek().v=='end'):
                st=s.stmt()
                if st: orelse.append(st)
        s.eat('KW','end')
        return If(cond,Block(body),Block(orelse))
    def while_stmt(s):
        s.eat('KW','while'); cond=s.expr(); s.eat('KW','do')
        body=[]
        while s.peek().t!='EOF' and not (s.peek().t=='KW' and s.peek().v=='end'):
            st=s.stmt()
            if st: body.append(st)
        s.eat('KW','end')
        return While(cond,Block(body))
    def expr(s): return s.or_expr()
    def or_expr(s):
        l=s.and_expr()
        while s.peek().t=='KW' and s.peek().v=='or':
            s.eat(); l=BinOp('or',l,s.and_expr())
        return l
    def and_expr(s):
        l=s.cmp_expr()
        while s.peek().t=='KW' and s.peek().v=='and':
            s.eat(); l=BinOp('and',l,s.cmp_expr())
        return l
    def cmp_expr(s):
        l=s.add_expr()
        while True:
            op=s.peek()
            if op.t=='OP' and op.v in ('==','~=','<','>','<=','>='):
                s.eat(); l=BinOp(op.v,l,s.add_expr())
            else: break
        return l
    def add_expr(s):
        l=s.mul_expr()
        while s.peek().t=='OP' and s.peek().v in ('+','-'):
            op=s.eat().v; l=BinOp(op,l,s.mul_expr())
        return l
    def mul_expr(s):
        l=s.unary()
        while s.peek().t=='OP' and s.peek().v in ('*','/','%'):
            op=s.eat().v; l=BinOp(op,l,s.unary())
        return l
    def unary(s):
        if s.peek().t=='OP' and s.peek().v=='-':
            s.eat(); return UnOp('-',s.unary())
        if s.peek().t=='KW' and s.peek().v=='not':
            s.eat(); return UnOp('not',s.unary())
        return s.postfix()
    def postfix(s):
        e=s.primary()
        while s.peek().t=='OP' and s.peek().v=='(':
            s.eat(); args=[]
            if not (s.peek().t=='OP' and s.peek().v==')'):
                args.append(s.expr())
                while s.accept(t='OP',v=','): args.append(s.expr())
            s.eat('OP',')'); e=Call(e,args)
        return e
    def primary(s):
        t=s.peek()
        if t.t=='NUMBER': s.eat(); return Num(t.v)
        if t.t=='STRING': s.eat(); return Str(t.v)
        if t.t=='KW' and t.v=='true': s.eat(); return Bool(True)
        if t.t=='KW' and t.v=='false': s.eat(); return Bool(False)
        if t.t=='KW' and t.v=='nil': s.eat(); return Nil()
        if t.t=='NAME': s.eat(); return Name(t.v)
        if t.t=='OP' and t.v=='(':
            s.eat(); e=s.expr(); s.eat('OP',')'); return e
        raise SyntaxError(f'Unexpected token {t}')

# ─── String obfuscation ─────────────────────────────────────────────────────
def xor_encrypt_string(s, key):
    return bytes(ord(c) ^ key[i % len(key)] for i, c in enumerate(s))

def obfuscate_string(s, rnd):
    key = [rnd.randint(1, 255) for _ in range(rnd.randint(4, 12))]
    enc = xor_encrypt_string(s, key)
    payload = base64.b64encode(enc).decode('ascii')
    return payload, key

# ─── Opcodes ────────────────────────────────────────────────────────────────
OP_NAMES = [
    'LOADK','LOADN','STORE','POP',
    'ADD','SUB','MUL','DIV','MOD',
    'EQ','NE','LT','LE','GT','GE',
    'NOT','NEG',
    'CALL','JMP','JMPF','RETURN','HALT',
    'CHKENV','CHKTRAP','NOP',
    'AND','OR','JMPT','JMPF_SC',
]
ARG_COUNTS = {
    'LOADK':1,'LOADN':1,'STORE':1,'POP':0,
    'ADD':0,'SUB':0,'MUL':0,'DIV':0,'MOD':0,
    'EQ':0,'NE':0,'LT':0,'LE':0,'GT':0,'GE':0,
    'NOT':0,'NEG':0,
    'CALL':2,'JMP':1,'JMPF':1,'RETURN':1,'HALT':0,
    'CHKENV':1,'CHKTRAP':1,'NOP':0,
    'AND':0,'OR':0,'JMPT':1,'JMPF_SC':1,
}

# ─── Compiler ───────────────────────────────────────────────────────────────
class Compiler:
    def __init__(s, seed):
        s.seed = seed
        rnd = random.Random(seed)
        s.rnd = rnd
        s.op_id = {}
        ids = list(range(1, 250))
        rnd.shuffle(ids)
        for i, name in enumerate(OP_NAMES):
            s.op_id[name] = ids[i]
        s.consts = []
        s.const_idx = {}
        s.instrs = []

    def const(s, val):
        if isinstance(val, str):
            payload, key = obfuscate_string(val, s.rnd)
            key_repr = '{' + ','.join(str(k) for k in key) + '}'
            return s.const_raw(('__STR_DEC__', payload, key_repr))
        key = repr(val)
        if key in s.const_idx: return s.const_idx[key]
        idx = len(s.consts)
        s.consts.append(val)
        s.const_idx[key] = idx
        return idx

    def const_raw(s, val):
        key = repr(val)
        if key in s.const_idx: return s.const_idx[key]
        idx = len(s.consts)
        s.consts.append(val)
        s.const_idx[key] = idx
        return idx

    def emit(s, name, *args):
        s.instrs.append(s.op_id[name])
        for a in args: s.instrs.append(a & 0xFF)

    def emit_math_const(s, n):
        rnd = s.rnd
        if not isinstance(n, int) or abs(n) >= 100000:
            s.emit('LOADK', s.const(n)); return
        if n == 0:
            a = rnd.randint(1, 500)
            s.emit('LOADK', s.const(a)); s.emit('LOADK', s.const(a)); s.emit('SUB'); return
        v = rnd.randint(0, 3)
        if v == 0:
            a = rnd.randint(-999, 999)
            s.emit('LOADK', s.const(n + a)); s.emit('LOADK', s.const(a)); s.emit('SUB')
        elif v == 1:
            f = rnd.randint(2, 50)
            s.emit('LOADK', s.const(n * f)); s.emit('LOADK', s.const(f)); s.emit('DIV')
        elif v == 2:
            a = rnd.randint(-999, 999); b = rnd.randint(-999, 999)
            s.emit('LOADK', s.const(n + a)); s.emit('LOADK', s.const(a)); s.emit('SUB')
            s.emit('LOADK', s.const(b)); s.emit('LOADK', s.const(b)); s.emit('SUB')
            s.emit('ADD')
        else:
            m = rnd.randint(2, 20); q, r = divmod(n, m)
            s.emit('LOADK', s.const(q)); s.emit('LOADK', s.const(m)); s.emit('MUL')
            s.emit('LOADK', s.const(r)); s.emit('ADD')

    def emit_math_float(s, f):
        a = 1 << s.rnd.randint(2, 10)
        s.emit('LOADK', s.const(f * a)); s.emit('LOADK', s.const(a)); s.emit('DIV')

    def compile_block(s, block):
        for st in block.stmts: s.compile_stmt(st)

    def compile_stmt(s, st):
        if isinstance(st, Local):
            for i, v in enumerate(st.vals):
                s.compile_expr(v); s.emit('STORE', s.const(st.names[i]))
            for n in st.names[len(st.vals):]:
                s.emit('LOADK', s.const(None)); s.emit('STORE', s.const(n))
        elif isinstance(st, Assign):
            for i, v in enumerate(st.vals):
                s.compile_expr(v); s.emit('STORE', s.const(st.names[i]))
        elif isinstance(st, If):
            s.compile_expr(st.cond)
            jmp_else = len(s.instrs); s.emit('JMPF', 0)
            s.compile_block(st.body)
            if st.orelse.stmts:
                jmp_end = len(s.instrs); s.emit('JMP', 0)
                s.instrs[jmp_else+1] = len(s.instrs)
                s.compile_block(st.orelse)
                s.instrs[jmp_end+1] = len(s.instrs)
            else:
                s.instrs[jmp_else+1] = len(s.instrs)
        elif isinstance(st, While):
            loop_start = len(s.instrs)
            s.compile_expr(st.cond)
            jmp_out = len(s.instrs); s.emit('JMPF', 0)
            s.compile_block(st.body)
            s.emit('JMP', loop_start)
            s.instrs[jmp_out+1] = len(s.instrs)
        elif isinstance(st, Return):
            for e in st.exprs: s.compile_expr(e)
            s.emit('RETURN', len(st.exprs))
        elif isinstance(st, Call):
            s.compile_expr(st); s.emit('POP')
        else:
            s.compile_expr(st); s.emit('POP')

    def compile_expr(s, e):
        if isinstance(e, Num):
            if isinstance(e.v, int): s.emit_math_const(e.v)
            else: s.emit_math_float(e.v)
        elif isinstance(e, Str): s.emit('LOADK', s.const(e.v))
        elif isinstance(e, Bool): s.emit('LOADK', s.const(e.v))
        elif isinstance(e, Nil): s.emit('LOADK', s.const(None))
        elif isinstance(e, Name): s.emit('LOADN', s.const(e.n))
        elif isinstance(e, BinOp):
            if e.op == 'and':
                s.compile_expr(e.l)
                j = len(s.instrs); s.emit('JMPF_SC', 0)
                s.compile_expr(e.r); s.instrs[j+1] = len(s.instrs)
            elif e.op == 'or':
                s.compile_expr(e.l)
                j = len(s.instrs); s.emit('JMPT', 0)
                s.compile_expr(e.r); s.instrs[j+1] = len(s.instrs)
            else:
                s.compile_expr(e.l); s.compile_expr(e.r)
                ops = {'+':'ADD','-':'SUB','*':'MUL','/':'DIV','%':'MOD',
                       '==':'EQ','~=':'NE','<':'LT','<=':'LE','>':'GT','>=':'GE'}
                s.emit(ops[e.op])
        elif isinstance(e, UnOp):
            s.compile_expr(e.e); s.emit('NEG' if e.op=='-' else 'NOT')
        elif isinstance(e, Call):
            for a in e.args: s.compile_expr(a)
            if isinstance(e.fn, Name):
                s.emit('CALL', s.const(e.fn.n), len(e.args))
            else:
                raise NotImplementedError('complex call')
        else:
            raise NotImplementedError(type(e))

    def finish(s):
        s.emit('HALT')
        return s.instrs

# ─── Silent anti-logger (30 checks, break on fail) ──────────────────────────
def _esc(s):
    out = []
    for c in s:
        o = ord(c)
        out.append(f'\\{o:03d}' if o <= 255 else c)
    return ''.join(out)

HARDENED_CHECKS = [
    (1, '''
    local __ok=pcall(function()
      local __f=".__mst_"..tostring(math.random(1,1000000000))
      writefile(__f,"67")
      if readfile(__f)~="67" then error() end
      if not isfile(__f) then error() end
      delfile(__f)
      if isfile(__f) then error() end
    end)
    if not __ok then break end
    '''),
    (2, f'''
    if pcall(string.char,nil) then break end
    if typeof(Vector3.new())~="{_esc("Vector3")}" then break end
    if typeof(1)~="{_esc("number")}" then break end
    if typeof("x")~="{_esc("string")}" then break end
    if typeof(nil)~="{_esc("nil")}" then break end
    if typeof(true)~="{_esc("boolean")}" then break end
    '''),
    (3, '''
    if pcall(function()
      local __e=game:GetService("EncodingService")
      local __b=buffer.fromstring("x")
      local __c=__e:CompressBuffer(__b,Enum.CompressionAlgorithm.Zstd,1)
      if buffer.tostring(__e:DecompressBuffer(__c,Enum.CompressionAlgorithm.Zstd))~="x" then error() end
    end) then break end
    '''),
    (4, f'''
    local __n={{{",".join('"%s"' % _esc(x) for x in
        ["Spy","__SPY__","___SPY___","Debugger","syn","krnl","Krnl","HexSpy","logger","__LOG__","intercept","getlogger"])}}}
    local __bad=false
    for __i=1,#__n do if rawget(_G,__n[__i])~=nil then __bad=true break end end
    if __bad then break end
    for __k in pairs(_G) do
      if type(__k)=="string"
        and (string.find(__k,"[Ss]py") or string.find(__k,"[Ll]ogger") or string.find(__k,"[Dd]ebugger"))
        and __k~="__DEBUG__" then __bad=true break end
    end
    if __bad then break end
    '''),
    (5, '''
    local __ok=pcall(function()
      local __p=Instance.new("Part")
      __p.Anchored=false __p.Parent=workspace
      task.wait(0.15)
      local __a=workspace:GetNumAwakeParts()
      __p.Anchored=true task.wait()
      local __b=workspace:GetNumAwakeParts()
      __p:Destroy()
      if __a<=__b then error() end
    end)
    if not __ok then break end
    '''),
    (6, '''
    local __ps=tostring(print)
    if string.match(__ps,"^function: 0x0000") then break end
    if string.match(__ps,"^table: ") then break end
    if type(print)~="function" or type(warn)~="function" or type(error)~="function" then break end
    '''),
    (7, '''
    if pcall(function() return game.ServerScriptService:GetChildren() end) then break end
    '''),
    (8, '''
    local __ok=pcall(function()
      local __i=debug.getinfo(function() end,"u")
      if type(__i)~="table" or __i.nups==nil or type(__i.nups)~="number" then error() end
    end)
    if not __ok then break end
    '''),
    (9, '''
    local __ok=pcall(function()
      local __mt={}
      setmetatable({},__mt) setreadonly(__mt,true)
      if pcall(function() __mt.__index={} end) then error() end
      if not isreadonly(__mt) then error() end
    end)
    if not __ok then break end
    '''),
    (10, '''
    local __s=os.clock()
    for __i=1,100000 do math.abs(__i) end
    if os.clock()-__s>=0.15 then break end
    '''),
    (11, '''
    local __ok=pcall(function()
      if typeof(gethui)~="function" then error() end
      local __h=gethui()
      local __fo=Instance.new("Folder")
      __fo.Parent=__h
      if not __h:FindFirstChild(__fo.Name) then error() end
      __fo:Destroy()
    end)
    if not __ok then break end
    '''),
    (12, '''
    if not rawequal(game,game) then break end
    if not rawequal(game:GetService("Players"),game:GetService("Players")) then break end
    if not rawequal(game:GetService("RunService"),game:GetService("RunService")) then break end
    local __p1,__p2=Instance.new("Part"),Instance.new("Part")
    if rawequal(__p1,__p2) then __p1:Destroy() __p2:Destroy() break end
    __p1:Destroy() __p2:Destroy()
    '''),
    (13, '''
    if getgenv then
      if getgenv()~=getgenv() then break end
      if rawget(getgenv(),"print")~=print then break end
      if rawget(getgenv(),"game")~=game then break end
    end
    '''),
    (14, '''
    if hookfunction then
      local __orig=math.abs local __fired=false
      local __hooked=hookfunction(__orig,function(...) __fired=true return __orig(...) end)
      __hooked(-1)
      hookfunction(__hooked,__orig)
      if not __fired then break end
    end
    '''),
    (15, '''
    if islclosure and iscclosure then
      local __n=function() end
      if not islclosure(__n) then break end
      if iscclosure(__n) then break end
    end
    '''),
    (16, '''
    if newcclosure and iscclosure then
      local __n=function() end
      local __c=newcclosure(__n)
      if __c==__n then break end
      if not iscclosure(__c) then break end
    end
    '''),
    (17, '''
    if select("#",unpack({1,2,3}))~=3 then break end
    if table.unpack and select("#",table.unpack({1,2,3}))~=3 then break end
    '''),
    (18, '''
    if string.char(65)~="A" then break end
    if string.byte("A")~=65 then break end
    if bit32.bxor(5,3)~=6 then break end
    if bit32.bxor(bit32.bxor(5,3),3)~=5 then break end
    if bit32.band(5,3)~=1 then break end
    if bit32.bor(5,3)~=7 then break end
    '''),
    (19, '''
    if not (math.huge>1e308) then break end
    if not (math.pi>3.14 and math.pi<3.15) then break end
    if os.clock()<0 then break end
    '''),
    (20, '''
    local __ok=pcall(function()
      local __co=coroutine.create(function() return 42 end)
      local __s,__v=coroutine.resume(__co)
      if not __s or __v~=42 then error() end
      local __w=coroutine.wrap(function() return 43 end)
      if __w()~=43 then error() end
    end)
    if not __ok then break end
    '''),
    (21, '''
    local __ok=pcall(function()
      local __a,__b=Instance.new("Part"),Instance.new("Part")
      if __a==__b then __a:Destroy() __b:Destroy() error() end
      __a:Destroy() __b:Destroy()
    end)
    if not __ok then break end
    '''),
    (22, '''
    if debug.info then
      local __ok,__r=pcall(function() return debug.info(2,"s") end)
      if not __ok or __r==nil then break end
    end
    '''),
    (23, '''
    if loadstring then
      local __f=loadstring("return 42")
      if not __f or __f()~=42 then break end
    end
    '''),
    (24, '''
    local __t={} rawset(__t,"a",1)
    if rawget(__t,"a")~=1 then break end
    if rawlen({1,2,3})~=3 then break end
    if rawlen(__t)~=0 then break end
    '''),
    (25, '''
    local __s,__n=string.gsub("aaa","a","b")
    if __s~="bbb" or __n~=3 then break end
    if string.format("%d",42)~="42" then break end
    if string.format("%.2f",3.14159)~="3.14" then break end
    '''),
    (26, '''
    local __b=buffer.create(4) buffer.writeu8(__b,0,65)
    if buffer.readu8(__b,0)~=65 then break end
    buffer.writef32(__b,0,3.5)
    if buffer.readf32(__b,0)~=3.5 then break end
    '''),
    (27, '''
    if utf8 and utf8.char and utf8.len then
      if utf8.len(utf8.char(65))~=1 or utf8.char(65)~="A" then break end
    end
    '''),
    (28, '''
    local __t=os.time()
    if type(__t)~="number" or __t<=0 then break end
    '''),
    (29, '''
    if string.pack and string.unpack then
      local __p=string.pack("i4",42)
      if #__p~=4 then break end
      if string.unpack("i4",__p)~=42 then break end
    end
    '''),
    (30, '''
    if select("#",1,nil,3)~=3 then break end
    if type(nil)~="nil" or type(0)~="number" or type("")~="string" then break end
    '''),
]

def build_checks_chain():
    parts = []
    for i, (cid, code) in enumerate(HARDENED_CHECKS):
        kw = 'if' if i == 0 else 'elseif'
        parts.append(f'{kw} __cid=={cid} then\n{code}')
    parts.append('end')
    return '\n'.join(parts)

def inject_anti_env(comp):
    rnd = random.Random(comp.seed ^ 0xA5A5)
    inv = {v:k for k,v in comp.op_id.items()}
    units, i = [], 0
    instrs = comp.instrs
    while i < len(instrs):
        opid = instrs[i]
        name = inv.get(opid)
        if name is None:
            units.append([opid]); i += 1; continue
        nargs = ARG_COUNTS.get(name, 0)
        units.append(instrs[i:i+1+nargs])
        i += 1 + nargs
    ids = [cid for cid, _ in HARDENED_CHECKS]
    rnd.shuffle(ids)
    chenv = [[comp.op_id['CHKENV'], cid] for cid in ids]
    traps = [[comp.op_id['CHKTRAP'], rnd.randrange(1, 200)] for _ in range(8)]
    n_start = max(3, len(chenv) // 3)
    for u in reversed(chenv[:n_start] + traps[:3]):
        units.insert(0, u)
    for u in chenv[n_start:] + traps[3:]:
        pos = rnd.randrange(len(units) + 1)
        units.insert(pos, u)
    flat = []
    for u in units: flat.extend(u)
    return flat

# ─── CFF ────────────────────────────────────────────────────────────────────
def build_cff_states(instrs, op_id, rnd):
    inv = {v:k for k,v in op_id.items()}
    ins_list = []
    i = 0
    while i < len(instrs):
        op = instrs[i]
        name = inv.get(op)
        if name is None:
            i += 1; continue
        n = ARG_COUNTS.get(name, 0)
        args = list(instrs[i+1:i+1+n])
        ins_list.append((i, name, args))
        i += 1 + n
    if not ins_list:
        return None, {}
    ids = rnd.sample(range(1000, 99000), len(ins_list))
    offset_to_sid = {off: sid for (off, _, _), sid in zip(ins_list, ids)}
    states = {}
    for idx, (off, name, args) in enumerate(ins_list):
        sid = ids[idx]
        opnum = op_id[name]
        fall = ids[idx+1] if idx+1 < len(ins_list) else 0
        if name == 'JMP':
            tgt = offset_to_sid.get(args[0], 0)
            states[sid] = (opnum, 0, 0, 0, tgt)
        elif name in ('JMPF', 'JMPF_SC', 'JMPT'):
            tgt = offset_to_sid.get(args[0], 0)
            states[sid] = (opnum, 0, 0, fall, tgt)
        elif name == 'HALT':
            states[sid] = (opnum, 0, 0, 0, 0)
        else:
            a = args[0] if len(args) > 0 else 0
            b = args[1] if len(args) > 1 else 0
            states[sid] = (opnum, a, b, fall, 0)
    return ids[0], states

def add_trampolines_and_decoys(states, op_id, rnd):
    nop = op_id['NOP']
    out = dict(states)
    for sid in list(states.keys()):
        opnum, a, b, nf, nj = out[sid]
        if nf and rnd.random() < 0.35:
            tid = rnd.randint(200000, 299999)
            while tid in out: tid = rnd.randint(200000, 299999)
            out[tid] = (nop, 0, 0, nf, 0)
            out[sid] = (opnum, a, b, tid, nj)
        opnum, a, b, nf, nj = out[sid]
        if nj and rnd.random() < 0.35:
            tid = rnd.randint(200000, 299999)
            while tid in out: tid = rnd.randint(200000, 299999)
            out[tid] = (nop, 0, 0, nj, 0)
            out[sid] = (opnum, a, b, nf, tid)
    real = list(states.keys())
    n_decoys = min(150, max(20, len(real) // 3))
    decoys = []
    for _ in range(n_decoys):
        did = rnd.randint(300000, 399999)
        while did in out: did = rnd.randint(300000, 399999)
        decoys.append(did)
    for did in decoys:
        tgt = rnd.choice(decoys) if rnd.random() < 0.7 else rnd.choice(real)
        out[did] = (nop, 0, 0, tgt, 0)
    return out

# ─── Serialization ──────────────────────────────────────────────────────────
def const_to_lua(c):
    if c is None: return 'nil'
    if isinstance(c, bool): return 'true' if c else 'false'
    if isinstance(c, (int, float)): return repr(c)
    if isinstance(c, str):
        esc = c.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n').replace('\r','\\r')
        return f'"{esc}"'
    if isinstance(c, tuple) and c[0] == '__STR_DEC__':
        _, payload, key_repr = c
        return '{__str=true,payload="%s",key=%s}' % (payload, key_repr)
    return 'nil'

def states_to_lua(states):
    lines = ['local __states={']
    for sid, (opnum, a, b, nf, nj) in states.items():
        lines.append(f'[{sid}]={{{opnum},{a},{b},{nf},{nj}}},')
    lines.append('}')
    return '\n'.join(lines)

# ═══════════════════════════════════════════════════════════════════════════
# Anti-tamper v3 (hard / soft / none)
# ═══════════════════════════════════════════════════════════════════════════
ANTI_TAMPER_CORE = r'''
local __at_fired = false
local __at_code, __at_text = nil, nil
local __R = {
    ["0x00"]="UNSPECIFIED_TAMPER",
    ["0x01"]="TIME_INTEGRITY_DRIFT_MISMATCH",
    ["0x02"]="HOOKFUNCTION_SANITY_HOOK_RETURN_MISMATCH",
    ["0x03"]="HOOKFUNCTION_SANITY_RESTORE_RETURN_MISMATCH",
    ["0x04"]="HOOKFUNCTION_SANITY_POINTER_MISMATCH",
    ["0x05"]="HOOKFUNCTION_SANITY_REHOOK_RETURN_MISMATCH",
    ["0x07"]="CRITICAL_FUNCTION_HOOKED_BOOT",
    ["0x09"]="CRITICAL_FUNCTION_HOOKED_RUNTIME",
    ["0x11"]="SERVER_TIME_OUT_OF_RANGE",
    ["0x12"]="TIME_INTEGRITY_MISSING_EPOCH_SOURCE",
    ["0x13"]="TIME_SOURCE_FROZEN",
    ["0x21"]="TRAP_PROXY_TOSTRING",
    ["0x24"]="TRAP_PROXY_LEN",
    ["0x26"]="TRAP_TABLE_TOSTRING",
    ["0x31"]="TRAP_TABLE_LEN",
    ["0x33"]="CRITICAL_FUNCTION_NON_NATIVE",
    ["0x34"]="THREAD_WAIT_ACCELERATED",
    ["0x36"]="THREAD_SPAWN_BLOCKED",
    ["0x38"]="THREAD_CHECK_NOT_STARTED",
    ["0x39"]="THREAD_DELAY_NOT_FIRED",
    ["0x40"]="THREAD_DELAY_TOO_EARLY",
    ["0x53"]="GLOBAL_METATABLE_CHANGED",
    ["0x54"]="REQUEST_FUNCTION_HOOKED",
    ["0x55"]="REQUEST_IS_LUA_CLOSURE",
    ["0x56"]="REQUEST_NOT_NATIVE_CLOSURE",
    ["0x68"]="WRITEFILE_BLOCKED",
    ["0x69"]="APPENDFILE_BLOCKED",
    ["0x6A"]="SETCLIPBOARD_BLOCKED",
    ["0x6B"]="TOCLIPBOARD_BLOCKED",
    ["0x6C"]="WRITE_CLIPBOARD_BLOCKED",
    ["0x6D"]="MAKEFOLDER_BLOCKED",
    ["0x6E"]="DELFOLDER_BLOCKED",
    ["0x6F"]="DELFILE_BLOCKED",
    ["0x70"]="SYN_WRITE_CLIPBOARD_BLOCKED",
    ["0x71"]="OTH_HOOK_FUNCTION_INVALID",
    ["0x72"]="OTH_UNHOOK_FUNCTION_INVALID",
    ["0x73"]="OTH_GET_ROOT_CALLBACK_INVALID",
    ["0x74"]="OTH_IS_HOOK_THREAD_INVALID",
    ["0x7A"]="CRITICAL_FUNCTION_OTH_HOOKED_BOOT",
    ["0x7B"]="CRITICAL_FUNCTION_OTH_HOOKED_RUNTIME",
}
local function __at_isNative(fn)
    if type(fn) ~= "function" then return false end
    if iscclosure then local ok,v=pcall(iscclosure,fn) if ok then return v==true end end
    if debug and debug.info then local ok,s=pcall(debug.info,fn,"s") if ok then return s=="[C]" end end
    if debug and debug.getinfo then local ok,i=pcall(debug.getinfo,fn,"S") if ok and type(i)=="table" then return i.what=="C" or i.source=="=[C]" end end
    return true
end
local function __at_isHooked(fn)
    if type(fn)~="function" then return false end
    if isfunctionhooked then local ok,v=pcall(isfunctionhooked,fn) if ok then return v==true end end
    return false
end
local function __at_checkEnv()
    if game==nil or type(game)=="table" then return "0x00" end
    if Instance==nil or type(Instance.new)~="function" then return "0x00" end
    local ok,players=pcall(function() return game:GetService("Players") end)
    if not ok or players==nil or typeof(players)~=typeof(game) then return "0x00" end
    return nil
end
local function __at_checkDebug()
    if not debug or type(debug.info)~="function" or type(debug.traceback)~="function" or type(string.match)~="function" then return "0x00" end
    local natives={debug.info,debug.traceback,pcall,string.match}
    for i=1,#natives do local ok,s=pcall(debug.info,natives[i],"s") if not ok or s~="[C]" then return "0x33" end end
    local ok,line=pcall(function() local function probe() return 1 end return debug.info(probe,"l") end)
    if not ok or type(line)~="number" then return "0x00" end
    local rawOk,rawErr=pcall(rawget)
    if rawOk or type(rawErr)~="string" then return "0x00" end
    if not string.match(rawErr,"^[^:]+:%d+:") then return "0x00" end
    if not (string.match(rawErr,"missing argument") or string.match(rawErr,"bad argument")) then return "0x00" end
    if string.match("rr6k3:231:jbkn7o","^[^:]+:(%d+):")~="231" then return "0x00" end
    if string.match("r9riq:-37:jbkn7o",".*:%s*(%-%d+):%s")~="-37" then return "0x00" end
    if string.match("n1os4:jbkn7o","^[^:]+:([a-z0-9]+)$")~="jbkn7o" then return "0x00" end
    if string.match("n1os4:jbkn7o","^__no_match__$")~=nil then return "0x00" end
    return nil
end
local function __at_checkHooks()
    if type(hookfunction)~="function" or type(restorefunction)~="function" then return nil end
    local function original(v) return v+1 end
    local function replacement(v) return v+2 end
    local before=original
    local okHook,hookRet=pcall(hookfunction,original,replacement)
    if not okHook then return "0x02" end
    if hookRet~=nil and type(hookRet)~="function" then return "0x02" end
    local okRestore,restoreRet=pcall(restorefunction,original)
    if not okRestore then return "0x03" end
    if restoreRet~=nil and type(restoreRet)~="function" then return "0x03" end
    if before~=original then return "0x04" end
    local okRehook,rehookRet=pcall(hookfunction,original,replacement)
    if not okRehook or (rehookRet~=nil and type(rehookRet)~="function") then pcall(restorefunction,original) return "0x05" end
    pcall(restorefunction,original)
    return nil
end
local function __at_checkCritical(runtime)
    local funcs={pcall,rawget,rawset,type,tostring,tonumber,setmetatable,getmetatable,
        string.byte,string.sub,string.match,string.char,table.concat,table.insert,math.floor,math.abs}
    for i=1,#funcs do
        local fn=funcs[i]
        if type(fn)=="function" then
            if __at_isHooked(fn) then return runtime and "0x09" or "0x07" end
            if not __at_isNative(fn) then return "0x33" end
        end
    end
    return nil
end
local __at_env=(getgenv and getgenv()) or _G
local __at_baseMeta=getmetatable and getmetatable(__at_env) or nil
local function __at_checkMeta()
    if getmetatable and getmetatable(((getgenv and getgenv()) or _G))~=__at_baseMeta then return "0x53" end
    return nil
end
local __at_request=__at_env.request or __at_env.http_request or (__at_env.syn and __at_env.syn.request)
local function __at_checkRequest()
    if type(__at_request)~="function" then return nil end
    if __at_isHooked(__at_request) then return "0x54" end
    if islclosure then local ok,v=pcall(islclosure,__at_request) if ok and v then return "0x55" end end
    if not __at_isNative(__at_request) then return "0x56" end
    return nil
end
local function __at_checkThreads()
    if type(task)~="table" then return nil end
    if type(task.wait)~="function" then return "0x38" end
    if type(task.spawn)~="function" then return "0x36" end
    if type(task.delay)~="function" then return "0x39" end
    local t1=os.clock() task.wait(0.1) local dt=os.clock()-t1
    if dt<0.05 then return "0x34" end
    if dt>1.0 then return "0x40" end
    local fired=false task.delay(0.05,function() fired=true end) task.wait(0.15)
    if not fired then return "0x39" end
    return nil
end
local function __at_canCall(fn,...)
    if type(fn)~="function" then return true end
    return pcall(fn,...)
end
local function __at_checkIo()
    if __at_env.writefile and not __at_canCall(__at_env.writefile,"syscure_probe_key","syscure_probe_message") then return "0x68" end
    if __at_env.appendfile and not __at_canCall(__at_env.appendfile,"syscure_probe_key","") then return "0x69" end
    if __at_env.setclipboard and not __at_canCall(__at_env.setclipboard,"syscure_probe_message") then return "0x6A" end
    if __at_env.toclipboard and not __at_canCall(__at_env.toclipboard,"syscure_probe_message") then return "0x6B" end
    if __at_env.write_clipboard and not __at_canCall(__at_env.write_clipboard,"syscure_probe_message") then return "0x6C" end
    if __at_env.makefolder and not __at_canCall(__at_env.makefolder,"syscure/cache") then return "0x6D" end
    if __at_env.delfolder and not __at_canCall(__at_env.delfolder,"syscure/cache") then return "0x6E" end
    if __at_env.delfile and not __at_canCall(__at_env.delfile,"syscure_probe_key") then return "0x6F" end
    if __at_env.syn and __at_env.syn.write_clipboard and not __at_canCall(__at_env.syn.write_clipboard,"syscure_probe_message") then return "0x70" end
    return nil
end
local function __at_checkOth(runtime)
    local oth=__at_env.oth
    if type(oth)~="table" then return nil end
    if oth.hook~=nil and type(oth.hook)~="function" then return "0x71" end
    local unhook=oth.unhook or oth.un_hook
    if unhook~=nil and type(unhook)~="function" then return "0x72" end
    if oth.get_root_callback~=nil and type(oth.get_root_callback)~="function" then return "0x73" end
    if oth.is_hook_thread~=nil and type(oth.is_hook_thread)~="function" then return "0x74" end
    if type(oth.hook)=="function" and __at_isHooked(oth.hook) then return runtime and "0x7B" or "0x7A" end
    return nil
end
local __at_epoch=os.time()
local function __at_checkTime()
    if type(__at_epoch)~="number" or __at_epoch<=0 then return "0x12" end
    local s=os.time()
    if type(s)~="number" then return "0x12" end
    if s<1700000000 then return "0x11" end
    if s>2200000000 then return "0x11" end
    if math.abs(s-__at_epoch)>86400 then return "0x01" end
    return nil
end
local function __at_checkGameTime()
    local da=workspace.DistributedGameTime task.wait(0.15)
    local db=workspace.DistributedGameTime
    if type(da)~="number" or type(db)~="number" or db<=da then return "0x13" end
    return nil
end
local function __at_checkHeartbeat()
    local ok,rs=pcall(function() return game:GetService("RunService") end)
    if not ok or not rs then return nil end
    local hits=0
    local conn=rs.Heartbeat:Connect(function() hits=hits+1 end)
    task.wait(0.2) conn:Disconnect()
    if hits<=0 then return "0x13" end
    return nil
end
local function __at_checkTrapProxy()
    local fired=false
    local proxy=setmetatable({},{__tostring=function() fired=true return "trap" end,__len=function() fired=true return 0 end})
    pcall(function() return tostring(proxy) end)
    if not fired then return "0x21" end
    fired=false pcall(function() return #proxy end)
    if not fired then return "0x24" end
    return nil
end
local function __at_checkTrapTable()
    local t={1,2,3,4,5}
    if #t~=5 then return "0x31" end
    local ts=tostring(t)
    if type(ts)~="string" or ts:sub(1,6)~="table:" then return "0x26" end
    return nil
end
local function __at_checkDataStore()
    local ok,obj=pcall(Instance.new,"DataStoreIncrementOptions")
    if not ok or not obj then return nil end
    local result=pcall(function()
        local data={hi=true,num=42,str="test"}
        obj:SetMetadata(data)
        local got=obj:GetMetadata()
        if not got or got.hi~=data.hi or got.num~=data.num or got.str~=data.str then error("ds") end
        obj:Destroy()
    end)
    if not result then return "0x00" end
    return nil
end
local function __at_checkTween()
    local ok,ts=pcall(function() return game:GetService("TweenService") end)
    if not ok or not ts then return nil end
    local result=pcall(function()
        local frame=Instance.new("Frame") frame.Position=UDim2.new(0,0,0,0)
        local info=TweenInfo.new(0.05) local goal={Position=UDim2.fromScale(1,1)}
        local t0=os.clock() local tw=ts:Create(frame,info,goal) tw:Play() tw.Completed:Wait()
        if os.clock()-t0<0.03 then error("fast") end
        frame:Destroy()
    end)
    if not result then return "0x00" end
    return nil
end
local function __at_fixHooks()
    if not pcall or not rawget or not getgenv then return end
    local ok,env=pcall(getgenv)
    if not ok or type(env)~="table" then return end
    local restore=rawget(env,"restorefunction")
    if type(restore)~="function" then return end
    local funcs={string and string.byte,setmetatable,pcall,rawget,rawset,pairs,type,getfenv,setfenv}
    for i=1,#funcs do local fn=funcs[i] if fn then pcall(restore,fn) end end
end
local function __at_run()
    local checks={__at_checkEnv,__at_checkDebug,__at_checkHooks,
        function() return __at_checkCritical(false) end,
        __at_checkMeta,__at_checkRequest,__at_checkThreads,
        __at_checkIo,function() return __at_checkOth(false) end,
        __at_checkTime,__at_checkGameTime,__at_checkHeartbeat,
        __at_checkTrapProxy,__at_checkTrapTable,__at_checkDataStore,__at_checkTween}
    for i=1,#checks do
        local ok,code=pcall(checks[i])
        if not ok then return "0x00","CHECK_EXCEPTION" end
        if code then return code,__R[code] or "TAMPER" end
    end
    return nil,nil
end
pcall(__at_fixHooks)
__at_code,__at_text=__at_run()
'''

ANTI_TAMPER_HARD = ANTI_TAMPER_CORE + r'''
if __at_code then
    if __at_fired then return end
    __at_fired=true
    pcall(function()
        local e=(getgenv and getgenv()) or _G
        if type(e)=="table" then
            e.__sc_crashed=true
            e.hookfunction=nil
            e.getrawmetatable=nil
            e.getnamecallmethod=nil
        end
    end)
    local __troll=[==[
  ⠛⠛⣿⣿⣿⣿⣿⡷⢶⣦⣶⣶⣤⣤⣤⣀
  ⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀
  ⠀⠀⠀⠉⠉⠉⠙⠻⣿⣿⠿⠿⠛⠛⠛⠻⣿⣿⣇
  ⠀⠀⢤⣀⣀⣀⠀⠀⢸⣷⡄⠀ ⣀⣤⣴⣿⣿⣿⣆
  ⠀⠀⠀⠀⠹⠏⠀⠀⠀⣿⣧⠀⠹⣿⣿⣿⣿⡿⣿
  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠛⠿⠇⢀⣼⣿⣿⠛⢯⡿⡟
  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠦⠴⢿⢿⣿⡿⠷⠀⣿
  ⠀⠀⠀⠀⠀⠀⠀⠙⣷⣶⣶⣤⣤⣤⣤⣤⣶⣦⠃
  ⠀⠀⠀⠀⠀⠀⠀⢐⣿⣾⣿⣿⣿⣿⣿⣿⣿⣿
  ⠀⠀⠀⠀⠀⠀⠀⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇
  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠻⢿⣿⣿⣿⣿⠟
  Syscure Anti-Tamper v3 — get a better environmental logger.
  ]==]
    task.spawn(function()
        task.wait(0.05)
        if type(print)=="function" then pcall(print,__troll) end
        error("[SC-AT] "..tostring(__at_text).." ("..tostring(__at_code)..")",0)
    end)
    while true do if coroutine and coroutine.yield then coroutine.yield() end end
end
'''

ANTI_TAMPER_SOFT = ANTI_TAMPER_CORE + r'''
if __at_code then return end
'''

# ═══════════════════════════════════════════════════════════════════════════
# NEW anti-env logger (silent via pcall + return)
# ═══════════════════════════════════════════════════════════════════════════
ANTI_ENV_PREAMBLE = r'''
if not pcall(function()
local _rg,_rs,_rq,_t,_ty,_pc,_er,_as,_sm,_gm,_ts,_dg,_dt,_sc,_sf,_sr,_sfind,_ssub,_ma,_mf,_ms,_mh,_oc,_tu,_tc,_ti,_tr=rawget,rawset,rawequal,type,typeof,pcall,error,assert,setmetatable,getmetatable,tostring,debug.getinfo,debug.traceback,string.char,string.format,string.rep,string.find,string.sub,math.abs,math.floor,math.sqrt,math.huge,os.clock,table.unpack,table.concat,table.insert,table.remove
local core={_dg,_pc,_t,_ty,_er,_as,_rg,_rs,_rq,_sm,_gm,_ts,_tu,_tc,_ti,_tr,_sc,_sf,_sr,_sfind,_ssub,_ma,_mf,_ms,_oc}
for i=1,#core do local ok,info=_pc(_dg,core[i],"S")if not ok or not info or info.what~="C"then _er()end end
if _ty(nil)~="nil"or _ty(true)~="boolean"or _ty(1)~="number"or _ty("s")~="string"or _ty({})~="table"or _ty(print)~="function"then _er()end
if 0.1+0.2~=0.30000000000000004 or 1/3~=0.3333333333333333 or _mh~=1/0 then _er()end
if _ms(4)~=2 or _mf(1.9)~=1 or _ma(-5)~=5 then _er()end
if _sf("%d",42)~="42"or _sr("a",3)~="aaa"or _ssub("hello",2,4)~="ell"or _sfind("hello","ll")~=3 or _sc(65)~="A"then _er()end
local tt={1,2,3}_ti(tt,4)if tt[4]~=4 or #tt~=4 then _er()end _tr(tt)if #tt~=3 then _er()end
local c1,c2=_oc(),_oc()if c2<c1 then _er()end
local pok,pr1,pr2=_pc(function()return 1,2 end)if not pok or pr1~=1 or pr2~=2 then _er()end
local eok,emsg=_pc(_er,"x")if eok or _t(emsg)~="string"then _er()end
if _pc(_sc,nil)then _er()end
local E={Vector3=Vector3,typeof=_ty,type=_t,debug=debug,table=table}
local function R(P)
local s,n,p={},0,1
local function push(v)n=n+1;_rs(s,n,v)end
local function pop()local v=_rg(s,n);_rs(s,n,nil);n=n-1;return v end
while true do
local o=_rg(P,p);if not o then return false end;p=p+1
if o==0 then return true
elseif o==1 then push(_rg(P,p));p=p+1
elseif o==2 then push(_rg(E,_rg(P,p)));p=p+1
elseif o==3 then local f=pop();if _t(f)~="function"then return false end;push(f())
elseif o==4 then local b,a=pop(),pop();push(a==b)
elseif o==5 then local b,a=pop(),pop();push(a~=b)
elseif o==6 then local b,a=pop(),pop();push(_rq(a,b))
elseif o==7 then push(_ty(pop())==_rg(P,p));p=p+1
elseif o==8 then local k=pop();local v=pop()if v==nil or k==nil then return false end local ok,val=_pc(_rg,v,k)if not ok then return false end push(val)
elseif o==9 then if not pop()then return false end
elseif o==11 then local c=_rg(P,p);p=p+1;local A={}for i=1,c do A[c-i+1]=pop()end local f=pop();if _t(f)~="function"then return false end local ok,val=_pc(f,_tu(A))if not ok then return false end push(val)
elseif o==12 then local x=_rg(s,n);_rs(s,n,_rg(s,n-1));_rs(s,n-1,x)
elseif o==13 then _rs(s,n,not _rg(s,n))
end
end
end
if not R({2,"Vector3",7,"table",9,2,"Vector3",1,"new",8,2,"type",12,11,1,1,"function",4,9,2,"debug",1,"getinfo",8,2,"Vector3",1,"new",8,1,"S",11,2,1,"what",8,1,"C",4,9,2,"Vector3",1,"zero",8,1,"X",8,1,0,4,9,2,"Vector3",1,"zero",8,1,"Y",8,1,0,4,9,2,"Vector3",1,"zero",8,1,"Z",8,1,0,4,9,2,"Vector3",1,"one",8,1,"X",8,1,1,4,9,2,"Vector3",1,"zero",8,2,"Vector3",1,"one",8,6,13,9,2,"Vector3",1,"new",8,3,7,"Vector3",9,0})then _er()end
local function S(t)local s=""for i=1,#t do s=s.._sc(t[i])end return s end
local function H(t)local k=S(t)return _rg(_G,k)~=nil end
local loggers={{83,112,121},{74,101,114,114,121},{107,111,108,101,110,118,108,111,103,103,101,114},{95,95,108,111,103,103,101,114},{95,95,104,111,111,107},{76,85,78,82},{108,117,110,114},{95,95,76,85,78,82},{76,85,78,82,95,86,77},{95,95,110,97,109,101,99,97,108,108},{95,95,105,110,100,101,120},{95,95,110,101,119,105,110,100,101,120}}
for i=1,#loggers do if H(loggers[i])then _er()end end
local lang={{112,121},{112,121,116,104,111,110},{112,121,116,104,111,110,51},{110,117,109,112,121},{80,73,76},{110,111,100,101},{100,101,110,111},{98,117,110},{110,112,109},{95,95,114,101,113,117,105,114,101},{112,114,111,99,101,115,115},{109,111,100,117,108,101},{101,120,112,111,114,116,115},{66,117,102,102,101,114},{95,95,100,105,114,110,97,109,101},{103,108,111,98,97,108,84,104,105,115},{103,108,111,98,97,108},{106,97,118,97},{74,97,118,97},{106,118,109},{114,117,115,116},{99,97,114,103,111},{119,97,115,109},{87,101,98,65,115,115,101,109,98,108,121},{102,102,105},{99,100,101,102},{119,105,110,100,111,119},{100,111,99,117,109,101,110,116},{102,101,116,99,104},{110,97,118,105,103,97,116,111,114}}
for i=1,#lang do if H(lang[i])then _er()end end
local tb=_dt("",1)if _t(tb)~="string"then _er()end
if tb:find(S({116,97,114,103,101,116,58}),1,true)or tb:find(S({58,53,48,58}),1,true)or tb:find(S({76,85,78,82,95}),1,true)then _er()end
local src=_dg(1,"S").source if _t(src)~="string"or src:find(S({116,97,114,103,101,116}),1,true)then _er()end
if _pc(function()local s=game:GetService("EncodingService")local b=buffer.fromstring("a")return buffer.tostring(s:DecompressBuffer(s:CompressBuffer(b,Enum.CompressionAlgorithm.Zstd,1),Enum.CompressionAlgorithm.Zstd))=="a"end)then _er()end
if _pc(function()game.ServerScriptService:GetChildren()end)then _er()end
local rA,rB=_pc(function()return Ray.new(Vector3.new(0,0,0),Vector3.new(1e-8,0,0)):ClosestPoint(Vector3.new(5,2,0))end)if not rA or _ty(rB)~="Vector3"or rB.X~=0 or rB.Y~=0 or rB.Z~=0 then _er()end
local rC,rD=_pc(function()return Ray.new(Vector3.new(0,0,0),Vector3.new(0.001,0,0)):Distance(Vector3.new(1,1,0))end)local rE,rF=_pc(function()return Ray.new(Vector3.new(0,0,0),Vector3.new(1,0,0)):Distance(Vector3.new(1,2,3))end)if not rC or not rE or rD~=1.4142135623730951 or rF~=3.605551275463989 then _er()end
local pn=Instance.new("Part")pn.Parent=workspace local nOk,n1,n2=_pc(pn.CanSetNetworkOwnership,pn)pn:Destroy()if not nOk or n1~=false or n2~=S({78,101,116,119,111,114,107,32,79,119,110,101,114,115,104,105,112,32,65,80,73,32,99,97,110,32,111,110,108,121,32,98,101,32,99,97,108,108,101,100,32,102,114,111,109,32,116,104,101,32,83,101,114,118,101,114,46})then _er()end
do local pa,pb=Instance.new("Part"),Instance.new("Part")
pa.Anchored=false pa.Size=Vector3.new(2,2,2)pa.Parent=workspace
pb.Anchored=false pb.Size=Vector3.new(4,4,4)pb.Parent=workspace
task.wait(0.1)
local ma,mb=pa.AssemblyMass,pb.AssemblyMass
pa:Destroy()pb:Destroy()
if _t(ma)~="number"or _t(mb)~="number"or ma<=0 or mb<=ma then _er()end
local rt=mb/ma
if rt<3 or rt>9 then _er()end
end
do local qm=Instance.new("Model")
local qa=Instance.new("Part",qm)local qb=Instance.new("Part",qm)
qa.Name="QA"
local qok=_pc(function()
if #qm:QueryDescendants("Part")~=2 then _er()end
if #qm:QueryDescendants("#QA")~=1 then _er()end
if #qm:QueryDescendants(":not(#QA)")~=1 then _er()end
if qm:QueryDescendants(":not(#QA)")[1]~=qb then _er()end
end)
qm:Destroy()
if not qok then _er()end
end
do local tr=Instance.new("TerrainRegion")
local tok=_pc(function()
if _ty(tr)~="Instance"then _er()end
if tr.ClassName~="TerrainRegion"then _er()end
if not tr:IsA("TerrainRegion")then _er()end
end)
tr:Destroy()
if not tok then _er()end
end
do local ts=game:GetService("TweenService")
local nv=Instance.new("NumberValue")nv.Value=0 nv.Parent=workspace
local tw=ts:Create(nv,TweenInfo.new(1,Enum.EasingStyle.Linear,Enum.EasingDirection.In),{Value=1})
tw:Play()
task.wait(0.5)
local mid=nv.Value
nv:Destroy()
if _t(mid)~="number"or mid<=0.3 or mid>=0.7 then _er()end
end
do local lp3=game:GetService("Players").LocalPlayer
if lp3 then
local sg=Instance.new("ScreenGui")sg.ResetOnSpawn=false sg.Parent=lp3.PlayerGui
local fr=Instance.new("Frame")fr.Size=UDim2.new(1,0,1,0)fr.Parent=sg
task.wait(0.1)
local ab=fr.AbsoluteSize
sg:Destroy()
if _t(ab.X)~="number"or ab.X<=100 or ab.Y<=100 then _er()end
end
end
do local cam=workspace.CurrentCamera
if cam then
if _ty(cam.CFrame)~="CFrame"or _ty(cam.Focus)~="CFrame"then _er()end
local vp=cam.ViewportSize
if _t(vp.X)~="number"or vp.X<=0 or vp.Y<=0 then _er()end
if cam.FieldOfView<=0 or cam.FieldOfView>120 then _er()end
if cam.CameraSubject==nil or not cam.CameraSubject:IsDescendantOf(game)then _er()end
local lp4=game:GetService("Players").LocalPlayer
local rp=RaycastParams.new()rp.FilterType=Enum.RaycastFilterType.Exclude
if lp4 and lp4.Character then rp.FilterDescendantsInstances={lp4.Character}end
local rr=workspace:Raycast(cam.CFrame.Position,Vector3.new(0,-1000,0),rp)
if rr then
if _ty(rr.Position)~="Vector3"or _ty(rr.Normal)~="Vector3"or _ty(rr.Material)~="EnumItem"then _er()end
if rr.Distance<=0 or rr.Normal.Y<=0 then _er()end
if rr.Instance==nil or not rr.Instance:IsDescendantOf(workspace)then _er()end
end
end
end
if _ts(print):match("^function: 0x0000")or _ts(warn):match("^function: 0x0000")or _ts(_er):match("^function: 0x0000")then _er()end
local ui=_dg(function()end,"u")if _t(ui)~="table"or ui.nups==nil or ui.nparams==nil then _er()end
local mt={}_sm({},mt)setreadonly(mt,true)if _pc(function()mt.__index={}end)then _er()end
if not _rq(game,game)or not _rq(game:GetService("Players"),game:GetService("Players"))or not _rq(game:GetService("RunService"),game:GetService("RunService"))or not _rq(game:GetService("Workspace"),workspace)then _er()end
local a1,a2=Instance.new("Part"),Instance.new("Part")local same=_rq(a1,a2)local selfs=_rq(a1,a1)a1:Destroy()a2:Destroy()if same or not selfs then _er()end
if _t(getfpscap)=="function"and _t(setfpscap)=="function"then local o=getfpscap()if not _pc(setfpscap,0)then _er()end if getfpscap()~=10000 then _pc(setfpscap,o);_er()end _pc(setfpscap,o)end
if _t(hookfunction)=="function"and _t(restorefunction)=="function"then local f1,f2=function()return 1 end,function()return 2 end local old=hookfunction(f1,f2)if _t(old)~="function"or f1()~=2 or old()~=1 then _er()end restorefunction(f1)local ro,re=_pc(restorefunction,f1)if ro or _ts(re)~="function is not hooked"then _er()end end
if _t(gethui)=="function"then local h=gethui()local fo=Instance.new("Folder")fo.Parent=h local ok=h:FindFirstChild(fo.Name)fo:Destroy()if not ok then _er()end end
if getgenv then if getgenv()~=getgenv()or _rg(getgenv(),"print")~=print then _er()end if _t(getgenv().print)~="function"then _er()end end
local t1=_oc()task.wait(0.05)local d1=_oc()-t1 if d1<0.04 or d1>0.2 then _er()end
local t2=_oc()for i=1,50000 do _ma(i)end if _oc()-t2>0.03 then _er()end
if not _pc(_sc,nil)then _er()end
local LL
local lok=_pc(function()LL=loadstring end)if not lok or _t(LL)~="function"then LL=nil end
if not LL then lok=_pc(function()LL=load end)if not lok or _t(LL)~="function"then LL=nil end end
if LL then
local q="local "for i=1,250 do q=q..(i>1 and","or"").."v"..i end
local lf,le=_pc(LL,q.."=1")
if lf~=nil then _er()end
if _t(le)~="string"or not le:find("200")then _er()end
end
local so1,so2=_pc(function()local function r(n)return n+r(n-1)end return r(1)end)
if so1 then _er()end
if _t(so2)~="string"or not so2:lower():find("stack")then _er()end
if _t(writefile)=="function"then local fn="."..math.random(1000,9999)..".t"writefile(fn,"x")if readfile(fn)~="x"or not isfile(fn)then delfile(fn);_er()end delfile(fn)if isfile(fn)or _pc(readfile,fn)then _er()end end
end)then return end
'''

# ─── Watermark ──────────────────────────────────────────────────────────────
WATERMARK = '''--[[
================================================================
  PROTECTED FILE
  This script is protected by an advanced VM obfuscation system.
  Reverse engineering, modification and redistribution are
  strictly prohibited. All integrity checks execute silently
  at runtime; any tampering results in silent termination.
================================================================
]]
'''

# ─── VM template ────────────────────────────────────────────────────────────
CFF_VM_TEMPLATE = r'''
__ANTI_TAMPER__
__ANTI_ENV__

local __states={__STATES__}
local __consts={__CONSTS__}
local __env={} local __stack={} local __sp=0
local __sinit=__INIT__

if __states[0]~=nil then return end
if #__consts<0 then return end

local function __push(v) __sp=__sp+1 __stack[__sp]=v end
local function __pop() local v=__stack[__sp] __stack[__sp]=nil __sp=__sp-1 return v end
local function __peek() return __stack[__sp] end
local function __dec(enc,key)
  local raw={}
  for i=1,#enc do raw[i]=string.char(bit32.bxor(string.byte(enc,i),key[(i-1)%#key+1])) end
  return table.concat(raw)
end

local __state=__sinit
while __state~=0 do
  local __st=__states[__state]
  if not __st then break end
  local __op=__st[1]
  if __op==__LOADK__ then
    local __v=__consts[__st[2]+1]
    if type(__v)=="table" and __v.__str then __push(__dec(__v.payload,__v.key)) else __push(__v) end
    __state=__st[4]
  elseif __op==__LOADN__ then
    __push(__env[__consts[__st[2]+1]]); __state=__st[4]
  elseif __op==__STORE__ then
    __env[__consts[__st[2]+1]]=__pop(); __state=__st[4]
  elseif __op==__POP__ then
    __pop(); __state=__st[4]
  elseif __op==__ADD__ then
    local b=__pop() local a=__pop() __push(a+b); __state=__st[4]
  elseif __op==__SUB__ then
    local b=__pop() local a=__pop() __push(a-b); __state=__st[4]
  elseif __op==__MUL__ then
    local b=__pop() local a=__pop() __push(a*b); __state=__st[4]
  elseif __op==__DIV__ then
    local b=__pop() local a=__pop() __push(a/b); __state=__st[4]
  elseif __op==__MOD__ then
    local b=__pop() local a=__pop() __push(a%b); __state=__st[4]
  elseif __op==__EQ__ then
    local b=__pop() local a=__pop() __push(a==b); __state=__st[4]
  elseif __op==__NE__ then
    local b=__pop() local a=__pop() __push(a~=b); __state=__st[4]
  elseif __op==__LT__ then
    local b=__pop() local a=__pop() __push(a<b); __state=__st[4]
  elseif __op==__LE__ then
    local b=__pop() local a=__pop() __push(a<=b); __state=__st[4]
  elseif __op==__GT__ then
    local b=__pop() local a=__pop() __push(a>b); __state=__st[4]
  elseif __op==__GE__ then
    local b=__pop() local a=__pop() __push(a>=b); __state=__st[4]
  elseif __op==__NOT__ then
    __push(not __pop()); __state=__st[4]
  elseif __op==__NEG__ then
    __push(-__pop()); __state=__st[4]
  elseif __op==__AND__ then
    local b=__pop() local a=__pop() __push(a and b); __state=__st[4]
  elseif __op==__OR__ then
    local b=__pop() local a=__pop() __push(a or b); __state=__st[4]
  elseif __op==__CALL__ then
    local __fnidx=__st[2] local __nargs=__st[3]
    local __args={} for __i=__nargs,1,-1 do __args[__i]=__pop() end
    local __fn=__consts[__fnidx+1]
    local __r
    if __fn=="print" then print(unpack(__args)) __r=nil
    else local __g=_G[__fn]
      if __g then __r=__g(unpack(__args)) else __r=nil end end
    __push(__r); __state=__st[4]
  elseif __op==__JMP__ then
    __state=__st[5]
  elseif __op==__JMPF__ then
    __state=__pop() and __st[4] or __st[5]
  elseif __op==__JMPF_SC__ then
    __state=__peek() and __st[4] or __st[5]
  elseif __op==__JMPT__ then
    __state=__peek() and __st[5] or __st[4]
  elseif __op==__RETURN__ then
    break
  elseif __op==__HALT__ then
    break
  elseif __op==__CHKENV__ then
    local __cid=__st[2]
    __CHECKS__
    __state=__st[4]
  elseif __op==__CHKTRAP__ then
    local __n=__st[2]
    if (__sp*(__sp+1))%2~=0 then break end
    if (__n*(__n+1))%2~=0 then break end
    if #__consts<0 then break end
    if __consts[__n+1]==__consts then break end
    __state=__st[4]
  elseif __op==__NOP__ then
    __state=__st[4]
  else
    __state=__st[4]
  end
end
'''

# ─── Bundler ────────────────────────────────────────────────────────────────
def assemble_cff(comp, states, init_state, anti_tamper='hard'):
    consts_lua = '{' + ','.join(const_to_lua(c) for c in comp.consts) + '}'
    repl = {}
    for name, oid in comp.op_id.items():
        repl[f'__{name}__'] = str(oid)
    repl['__STATES__'] = states_to_lua(states)
    repl['__CONSTS__'] = consts_lua
    repl['__INIT__'] = str(init_state)
    repl['__CHECKS__'] = build_checks_chain()
    if anti_tamper == 'hard':
        repl['__ANTI_TAMPER__'] = ANTI_TAMPER_HARD
    elif anti_tamper == 'soft':
        repl['__ANTI_TAMPER__'] = ANTI_TAMPER_SOFT
    else:
        repl['__ANTI_TAMPER__'] = ''
    repl['__ANTI_ENV__'] = ANTI_ENV_PREAMBLE
    def sub(m): return repl.get(m.group(0), m.group(0))
    return re.sub(r'__[A-Z_0-9]+__', sub, CFF_VM_TEMPLATE)

def build_bundle(source, seed=0, min_size=23000, anti_tamper='hard'):
    toks = lex(source)
    ast = Parser(toks).parse()
    comp = Compiler(seed)
    comp.compile_block(ast)
    comp.finish()
    protected = inject_anti_env(comp)
    rnd = random.Random(seed ^ 0xBEEF)
    init_state, states = build_cff_states(protected, comp.op_id, rnd)
    states = add_trampolines_and_decoys(states, comp.op_id, rnd)
    out = assemble_cff(comp, states, init_state, anti_tamper)
    full = WATERMARK + out
    if len(full) < min_size:
        gap = min_size - len(full)
        nop = comp.op_id['NOP']
        extra = dict(states)
        real = list(states.keys())
        for k in range(gap // 40 + 60):
            did = 400000 + k
            while did in extra: did += 1
            extra[did] = (nop, 0, 0, rnd.choice(real), 0)
        full = WATERMARK + assemble_cff(comp, extra, init_state, anti_tamper)
    return full

# ─── CLI ────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--output', default='obfuscated.lua')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--min-size', type=int, default=23000)
    ap.add_argument('--anti-tamper', choices=['hard', 'soft', 'none'], default='hard',
                    help='hard=crash+troll, soft=silent return, none=disabled')
    ap.add_argument('--no-anti-tamper', action='store_true',
                    help='Alias for --anti-tamper none')
    args = ap.parse_args()
    mode = 'none' if args.no_anti_tamper else args.anti_tamper
    with open(args.input, encoding='utf-8') as f:
        src = f.read()
    out = build_bundle(src, seed=args.seed, min_size=args.min_size, anti_tamper=mode)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(out)

if __name__ == '__main__':
    main()
