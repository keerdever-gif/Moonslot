#!/usr/bin/env python3
# obfuscator.py — Luau VM obfuscator (CFF + math-code + silent anti-logger)
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

# ─── AST + Parser ───────────────────────────────────────────────────────────
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

# ─── Compiler (math-code integrado) ─────────────────────────────────────────
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

# ─── Hardened silent anti-logger ────────────────────────────────────────────
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

# ─── Anti-logger injection (distribuida) ────────────────────────────────────
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

# ─── CFF (state machine real) ───────────────────────────────────────────────
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

# ─── Serialización ──────────────────────────────────────────────────────────
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

# ─── VM template ────────────────────────────────────────────────────────────
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

CFF_VM_TEMPLATE = r'''
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
def assemble_cff(comp, states, init_state):
    consts_lua = '{' + ','.join(const_to_lua(c) for c in comp.consts) + '}'
    repl = {}
    for name, oid in comp.op_id.items():
        repl[f'__{name}__'] = str(oid)
    repl['__STATES__'] = states_to_lua(states)
    repl['__CONSTS__'] = consts_lua
    repl['__INIT__'] = str(init_state)
    repl['__CHECKS__'] = build_checks_chain()
    def sub(m): return repl.get(m.group(0), m.group(0))
    return re.sub(r'__[A-Z_0-9]+__', sub, CFF_VM_TEMPLATE)

def build_bundle(source, seed=0, min_size=23000):
    toks = lex(source)
    ast = Parser(toks).parse()
    comp = Compiler(seed)
    comp.compile_block(ast)
    comp.finish()
    protected = inject_anti_env(comp)
    rnd = random.Random(seed ^ 0xBEEF)
    init_state, states = build_cff_states(protected, comp.op_id, rnd)
    states = add_trampolines_and_decoys(states, comp.op_id, rnd)
    out = assemble_cff(comp, states, init_state)
    full = WATERMARK + out
    if len(full) < min_size:
        gap = min_size - len(full)
        nop = comp.op_id['NOP']
        extra_states = dict(states)
        real = list(states.keys())
        n_extra = gap // 40 + 60
        for k in range(n_extra):
            did = 400000 + k
            while did in extra_states: did += 1
            tgt = rnd.choice(real)
            extra_states[did] = (nop, 0, 0, tgt, 0)
        full = WATERMARK + assemble_cff(comp, extra_states, init_state)
    return full

# ─── CLI (silencioso) ───────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--output', default='obfuscated.lua')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--min-size', type=int, default=23000)
    args = ap.parse_args()
    with open(args.input, encoding='utf-8') as f:
        src = f.read()
    out = build_bundle(src, args.seed, args.min_size)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(out)

if __name__ == '__main__':
    main()
