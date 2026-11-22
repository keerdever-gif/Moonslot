import re
import random
import argparse

HEADER = '''--[[
  Protected by Moonslot - Custom Bytecode VM
  Unauthorized reproduction or distribution is prohibited.
]]\n'''

# ── ANTI-TAMPER SILENCIOSO Y DEFENSIVO ────────────────────────────────────
ANTI_TAMPER_CORE = r'''
local function _get_integrity_offset()
    local offset = 0
    -- 1. Verificación conductual
    local ok_bxor, res_bxor = pcall(function() return bit32.bxor(5, 5) end)
    if not ok_bxor or res_bxor ~= 0 then offset = offset + 1 end
    local ok_concat, res_concat = pcall(function() return table.concat({"a", "b"}) end)
    if not ok_concat or res_concat ~= "ab" then offset = offset + 1 end
    if type(pcall) ~= "function" or type(type) ~= "function" then offset = offset + 1 end

    -- 2. Inspección de entorno
    local env = _G
    if type(getgenv) == "function" then
        local ok, genv = pcall(getgenv)
        if ok and type(genv) == "table" then env = genv end
    end
    if type(getfenv) == "function" then
        local ok, fenv = pcall(getfenv)
        if ok and type(fenv) ~= "table" then offset = offset + 1 end
    end
    if type(setfenv) == "function" then
        local ok, _ = pcall(setfenv)
        if not ok then offset = offset + 1 end
    end

    -- 3. Detección de Env Loggers
    if type(debug) == "table" then
        if type(debug.getinfo) == "function" then
            local ok, info = pcall(debug.getinfo, 1)
            if ok and info and (info.what == "C" or info.source == "=[C]") then offset = offset + 1 end
        end
        if type(debug.gethook) == "function" then
            local ok, hook = pcall(debug.gethook)
            if ok and hook ~= nil then offset = offset + 1 end
        end
    end

    -- 4. Detección de hooks
    local hooked = env["isfunctionhooked"] or env["is_function_hooked"]
    if type(hooked) == "function" then
        local check_fns = {pcall, type, tostring, next, pairs, ipairs, rawget, rawset, setmetatable}
        for _, fn in ipairs(check_fns) do
            local ok, res = pcall(hooked, fn)
            if ok and res == true then offset = offset + 1 end
        end
    end
    return offset
end
'''

_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"

def randomName() -> str:
    return "_" + "".join(random.choice(_BASE36) for _ in range(6)) + str(random.randint(0, 9999))

# ── VARIABLES OPACAS ──────────────────────────────────────────────────────
def generate_opaque_var(var_name):
    val = random.randint(2, 50)
    r = random.randint(1, 100)
    op = random.choice(['bxor', 'band', 'bor'])
    if op == 'bxor': expr = f"bit32.bxor({r}, {r}) + {val}"
    elif op == 'band': expr = f"bit32.band({r}, {r}) + {val}"
    else: expr = f"bit32.bor({r}, {r}) - {r} + {val}"
    return f"local {var_name} = {expr} ", val

def generate_opaque_predicate() -> str:
    r = random.randint(1, 100)
    return f"(bit32.bxor({r}, {r}) == 0)"

def generateSingleJunkLine() -> str:
    r = random.random()
    pred = generate_opaque_predicate()
    v = randomName()
    if r < 0.2: return f"if {pred} then local {v}={random.randint(0, 998)} end "
    elif r < 0.4: return f"local {v}={{}} for i=1,5 do {v}[i]=string.rep('x',10) end "
    elif r < 0.6: return f"do local {v} = setmetatable({{}}, {{__index=function() return math.random() end}}) end "
    elif r < 0.8: return f"pcall(function() if {pred} then return string.len('random') end end) "
    else: return f"local {v}=math.floor(math.random(1, 500)) "

# ── TOKENIZADOR Y MINIFICADOR ─────────────────────────────────────────────
def tokenize_lua(code: str):
    tokens = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if c in '"\'':
            quote = c; j = i + 1
            while j < n and code[j] != quote:
                if code[j] == '\\': j += 1
                j += 1
            tokens.append(code[i:j+1]); i = j + 1
        elif c == '[':
            m = re.match(r'\[(=*)\[', code[i:])
            if m:
                eq = m.group(1); close = ']' + eq + ']'
                j = code.find(close, i)
                if j != -1: tokens.append(code[i:j+len(close)]); i = j + len(close); continue
            tokens.append(c); i += 1
        elif c.isspace(): i += 1
        elif c.isalnum() or c == '_':
            j = i
            while j < n and (code[j].isalnum() or code[j] == '_'): j += 1
            tokens.append(code[i:j]); i = j
        else:
            tokens.append(c); i += 1
    return tokens

def minify_payload(code):
    code = re.sub(r'--\[\[.*?\]\]', '', code, flags=re.DOTALL)
    code = re.sub(r'--[^\n]*', '', code)
    tokens = tokenize_lua(code)
    out = []
    for idx, tok in enumerate(tokens):
        out.append(tok)
        if idx < len(tokens) - 1:
            nxt = tokens[idx+1]
            if (tok[-1].isalnum() or tok[-1] == '_') and (nxt[0].isalnum() or nxt[0] == '_'): out.append(' ')
    return ''.join(out)

# ── COMPILADOR A BYTECODE (PYTHON) ────────────────────────────────────────
class BytecodeCompiler:
    def __init__(self):
        self.ops = []
        self.const_pool = [None] # 1-based
        self.const_map = {}
        self.next_reg = 0
        self.locals = {}
    
    def add_const(self, val):
        if isinstance(val, bool): key = ('bool', val)
        elif isinstance(val, int): key = ('int', val)
        elif isinstance(val, float): key = ('float', val)
        elif isinstance(val, str): key = ('str', val)
        else: key = ('nil', None)
        
        if key in self.const_map: return self.const_map[key]
        idx = len(self.const_pool)
        self.const_pool.append(val)
        self.const_map[key] = idx
        return idx
    
    def new_reg(self):
        r = self.next_reg
        self.next_reg += 1
        return r
    
    def emit(self, op, a, b):
        self.ops.append((op & 0xFFFFFFFF, a & 0xFFFFFFFF, b & 0xFFFFFFFF))
    
    def _unescape(self, s):
        out = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                c = s[i+1]
                if c == 'n': out.append('\n')
                elif c == 't': out.append('\t')
                elif c == 'r': out.append('\r')
                elif c == '\\': out.append('\\')
                elif c == '"': out.append('"')
                elif c == "'": out.append("'")
                else: out.append(c)
                i += 2
            else:
                out.append(s[i])
                i += 1
        return ''.join(out)
    
    def compile_expr(self, tokens, pos):
        tok = tokens[pos] if pos < len(tokens) else None
        if tok is None: return 0, pos
        
        # Literales
        if tok.startswith('"') or tok.startswith("'"):
            val = self._unescape(tok[1:-1])
            r = self.new_reg()
            self.emit(1, r, self.add_const(val))
            return r, pos + 1
        
        if re.match(r'^-?\d+(\.\d+)?$', tok):
            val = float(tok) if '.' in tok else int(tok)
            r = self.new_reg()
            self.emit(1, r, self.add_const(val))
            return r, pos + 1
            
        if tok == 'true':
            r = self.new_reg(); self.emit(1, r, self.add_const(True)); return r, pos + 1
        if tok == 'false':
            r = self.new_reg(); self.emit(1, r, self.add_const(False)); return r, pos + 1
        if tok == 'nil':
            r = self.new_reg(); self.emit(1, r, self.add_const(None)); return r, pos + 1
        
        # Identificadores (Globales o Locales)
        if tok[0].isalpha() or tok[0] == '_':
            if tok in self.locals:
                r = self.new_reg()
                self.emit(10, r, self.locals[tok]) # MOVE
            else:
                r = self.new_reg()
                self.emit(2, r, self.add_const(tok)) # GET_GLOBAL
            pos += 1
            
            while pos < len(tokens):
                t = tokens[pos]
                if t == '.':
                    pos += 1
                    if pos < len(tokens):
                        field = tokens[pos]; pos += 1
                        self.emit(3, r, self.add_const(field))
                elif t == ':':
                    pos += 1
                    if pos < len(tokens):
                        method = tokens[pos]; pos += 1
                        self.emit(3, r, self.add_const(method))
                        if pos < len(tokens) and tokens[pos] == '(':
                            pos += 1
                            arg_regs = [r] # self
                            while pos < len(tokens) and tokens[pos] != ')':
                                ar, pos = self.compile_expr(tokens, pos)
                                arg_regs.append(ar)
                                if pos < len(tokens) and tokens[pos] == ',': pos += 1
                            if pos < len(tokens) and tokens[pos] == ')': pos += 1
                            
                            for i, ar in enumerate(arg_regs):
                                target = r + 1 + i
                                if ar != target: self.emit(10, target, ar)
                            self.emit(4, r, len(arg_regs))
                elif t == '(':
                    pos += 1
                    arg_regs = []
                    while pos < len(tokens) and tokens[pos] != ')':
                        ar, pos = self.compile_expr(tokens, pos)
                        arg_regs.append(ar)
                        if pos < len(tokens) and tokens[pos] == ',': pos += 1
                    if pos < len(tokens) and tokens[pos] == ')': pos += 1
                    
                    for i, ar in enumerate(arg_regs):
                        target = r + 1 + i
                        if ar != target: self.emit(10, target, ar)
                    self.emit(4, r, len(arg_regs))
                else:
                    break
            return r, pos
            
        return 0, pos + 1
    
    def compile_statements(self, tokens):
        pos = 0
        n = len(tokens)
        while pos < n:
            tok = tokens[pos]
            if tok == 'local':
                pos += 1
                if pos < n:
                    name = tokens[pos]; pos += 1
                    x_reg = self.new_reg()
                    self.locals[name] = x_reg
                    if pos < n and tokens[pos] == '=':
                        pos += 1
                        val_reg, pos = self.compile_expr(tokens, pos)
                        if val_reg != x_reg: self.emit(10, x_reg, val_reg)
            elif tok == 'return':
                pos += 1
                if pos < n and tokens[pos] not in ('end', ';'):
                    r, pos = self.compile_expr(tokens, pos)
                    self.emit(6, r, 0)
                else: self.emit(6, 0, 0)
            elif tok[0].isalpha() or tok[0] == '_':
                # Detectar asignación simple: x = expr
                if pos + 1 < n and tokens[pos+1] == '=':
                    name = tok; pos += 2
                    val_reg, pos = self.compile_expr(tokens, pos)
                    if name in self.locals: self.emit(10, self.locals[name], val_reg)
                    else: self.emit(7, self.add_const(name), val_reg)
                else:
                    r, pos = self.compile_expr(tokens, pos)
            else:
                pos += 1
        
        self.emit(6, 0, 0) # Final RET
        return self.ops, self.const_pool

def compile_to_bytecode(code):
    tokens = tokenize_lua(code)
    compiler = BytecodeCompiler()
    return compiler.compile_statements(tokens)

def generate_bytecode(ops, const_pool, seed):
    encoded_ops = []
    acc = seed
    for pc, (op, a, b) in enumerate(ops, start=1):
        enc_op = op ^ ((acc + pc) & 0xFFFFFFFF)
        enc_a = a ^ (acc & 0xFFFFFFFF)
        enc_b = b ^ ((pc * 7) & 0xFFFFFFFF)
        acc = ((acc * 31 + op + pc) % 256 + 256) % 256
        encoded_ops.append(f"{{{enc_op},{enc_a},{enc_b}}}")
    
    def repr_val(v):
        if v is None: return "nil"
        if isinstance(v, bool): return "true" if v else "false"
        if isinstance(v, str):
            esc = v.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            return f'"{esc}"'
        return str(v)
    
    cp_str = "{" + ",".join(repr_val(c) for c in const_pool[1:]) + "}"
    return "{" + ",".join(encoded_ops) + "}", cp_str

# ── POLIMORFISMO (CAPAS) ──────────────────────────────────────────────────
def build_vm_table_style(inner_code, config):
    store = randomName(); mt = randomName(); dispatch = randomName()
    op_vars = []; out = ""
    for _ in range(config["opaque_vars"]):
        ov = randomName(); code, val = generate_opaque_var(ov); out += code; op_vars.append((ov, val))
    out += f"local {store}={{}} local {mt}={{__index=function(t,k) return {store}[k] end}} "
    out += f"local {dispatch}=setmetatable({{}},{mt}) "
    handler_count = random.randint(4, 7); real_idx = random.randint(1, handler_count)
    for i in range(1, handler_count + 1):
        if i == real_idx: out += f"{store}[{i}]=function(lM) {generateSingleJunkLine()}{generateSingleJunkLine()} {inner_code} end "
        else: out += f"{store}[{i}]=function(lM) {generateSingleJunkLine()} return nil end "
    conds = [f"{ov} {random.choice(['==', '>=', '<='])} {val}" for ov, val in op_vars]
    cond_str = " and ".join(conds) if conds else "true"
    out += f"local _state=1 while _state > 0 do "
    out += f"if _state==1 and {cond_str} then {dispatch}[{real_idx}]({{}}) _state=0 end "
    out += "end "
    return out

def build_vm_ifchain_style(inner_code, config):
    out = ""; state_var = randomName()
    branches = [random.randint(100, 999) for _ in range(random.randint(3, 5))]
    real_branch = random.choice(branches); initial_state = real_branch
    op_vars = []
    for _ in range(config["opaque_vars"]):
        ov = randomName(); code, val = generate_opaque_var(ov); out += code; op_vars.append((ov, val))
    out += f"local {state_var} = {initial_state} while {state_var} ~= 0 do "
    conds = [f"{ov} {random.choice(['==', '>=', '<='])} {val}" for ov, val in op_vars]
    cond_str = " and ".join(conds) if conds else "true"
    for i, b in enumerate(branches):
        prefix = "if" if i == 0 else "elseif"
        if b == real_branch: out += f"{prefix} {state_var} == {b} and {cond_str} then {generateSingleJunkLine()} {inner_code} {state_var} = 0 "
        else: out += f"{prefix} {state_var} == {b} then {state_var} = {random.randint(0, 1)} "
    out += "else break end end "
    return out

def build_vm_cff_style(inner_code, config):
    var_s = randomName(); s1 = random.randint(1000, 1999); s2 = random.randint(2000, 2999); s3 = random.randint(3000, 3999)
    out = f"local {var_s} = {s1} "
    op_vars = []
    for _ in range(config["opaque_vars"]):
        ov = randomName(); code, val = generate_opaque_var(ov); out += code; op_vars.append((ov, val))
    conds = [f"{ov} {random.choice(['==', '>=', '<='])} {val}" for ov, val in op_vars]
    cond_str = " and ".join(conds) if conds else "true"
    out += f"repeat "
    out += f"if {var_s} == {s1} and {cond_str} then {generateSingleJunkLine()} {inner_code} {var_s} = {s2} "
    out += f"elseif {var_s} == {s2} then {var_s} = {s3} "
    out += f"else {var_s} = {s3} end "
    out += f"until {var_s} == {s3} "
    return out

def build_polymorphic_layer(inner_code, config):
    mode = config["polymorphic_mode"]
    if mode == "auto" or mode == "mixed": mode = random.choice(["table", "ifchain", "cff"])
    if mode == "table": return build_vm_table_style(inner_code, config)
    elif mode == "ifchain": return build_vm_ifchain_style(inner_code, config)
    else: return build_vm_cff_style(inner_code, config)

# ── NÚCLEO DE LA VM ───────────────────────────────────────────────────────
def buildTrueVM(payloadStr: str, config) -> str:
    seed = random.randint(10, 250)
    raw_ops, const_pool = compile_to_bytecode(payloadStr)
    encoded_ops_str, const_pool_str = generate_bytecode(raw_ops, const_pool, seed)
    
    vmCore = f"{ANTI_TAMPER_CORE}\n"
    vmCore += f"local _offset = _get_integrity_offset() "
    vmCore += f"local _seed = {seed} + _offset "
    vmCore += f"local _consts = {const_pool_str} "
    vmCore += f"local _ops = {encoded_ops_str} "
    
    vmCore += "local pc = 1 local acc = _seed local regs = {} local running = true "
    vmCore += "local env = (getgenv and type(getgenv)=='function') and getgenv() or _G "
    vmCore += "local unpack_fn = table.unpack or unpack "
    
    vmCore += "while running and pc <= #_ops do "
    vmCore += "local raw = _ops[pc] "
    vmCore += "local op = bit32.bxor(raw[1], bit32.band(acc + pc, 0xFFFFFFFF)) "
    vmCore += "local a = bit32.bxor(raw[2] or 0, bit32.band(acc, 0xFFFFFFFF)) "
    vmCore += "local b = bit32.bxor(raw[3] or 0, bit32.band(pc * 7, 0xFFFFFFFF)) "
    vmCore += "acc = ((acc * 31 + op + pc) % 256 + 256) % 256 "
    vmCore += "pc = pc + 1 "
    
    vmCore += "if op == 1 then regs[a] = _consts[b] "
    vmCore += "elseif op == 2 then regs[a] = env[_consts[b]] "
    vmCore += "elseif op == 3 then regs[a] = regs[a][_consts[b]] "
    vmCore += "elseif op == 4 then "
    vmCore += "  local fn = regs[a] local args = {} "
    vmCore += "  for i = 1, b do args[i] = regs[a + i] end "
    vmCore += "  if type(fn) == 'function' then regs[a] = fn(unpack_fn(args)) end "
    vmCore += "elseif op == 5 then pc = b "
    vmCore += "elseif op == 6 then running = false "
    vmCore += "elseif op == 7 then env[_consts[a]] = regs[b] "
    vmCore += "elseif op == 8 then regs[a][_consts[b]] = regs[a+1] "
    vmCore += "elseif op == 9 then if not regs[a] then pc = b end "
    vmCore += "elseif op == 10 then regs[a] = regs[b] "
    vmCore += "end end "
    
    return vmCore

# ── ORQUESTADOR PRINCIPAL ─────────────────────────────────────────────────
def obfuscate(sourceCode: str, config: dict) -> str:
    if not sourceCode: return '--ERROR'
    random.seed(config["seed"])

    minified_user_code = minify_payload(sourceCode)
    final_user_script = buildTrueVM(minified_user_code, config)
    
    for _ in range(config["vm_layers"]):
        final_user_script = build_polymorphic_layer(final_user_script, config)
        
    final_user_script = f"(function() pcall(function() {final_user_script} end) end)()"

    protection_payload = minify_payload("pcall(function() if type(_G) ~= 'table' then error('g') end end)")
    anti_tamper_final = buildTrueVM(protection_payload, config)
    for _ in range(config["anti_tamper_layers"]):
        anti_tamper_final = build_polymorphic_layer(anti_tamper_final, config)

    final_code = (
        f"local _mc={{}} for i=1,1500 do _mc[i]=string.rep('X',50) end _mc=nil pcall(collectgarbage) "
        f"{anti_tamper_final} "
        f"{final_user_script}"
    )
    return HEADER + minify_payload(final_code)

def main():
    parser = argparse.ArgumentParser(description="Moonslot - Custom Bytecode VM")
    parser.add_argument('input', help="Archivo de entrada Lua")
    parser.add_argument('-o', '--output', default='obfuscated.lua', help="Archivo de salida")
    parser.add_argument('--seed', type=int, default=0, help="Semilla")
    parser.add_argument('--vm-layers', type=int, default=5, help="Capas de VM")
    parser.add_argument('--anti-tamper-layers', type=int, default=3, help="Capas Anti-Tamper")
    parser.add_argument('--opaque-vars', type=int, default=2, help="Variables opacas")
    parser.add_argument('--polymorphic-mode', choices=['auto', 'table', 'ifchain', 'cff', 'mixed'], default='auto', help="Estilo")

    args, unknown = parser.parse_known_args()
    config = {
        "seed": args.seed, "vm_layers": args.vm_layers,
        "anti_tamper_layers": args.anti_tamper_layers,
        "opaque_vars": args.opaque_vars, "polymorphic_mode": args.polymorphic_mode
    }

    try:
        with open(args.input, encoding='utf-8') as f: src = f.read()
        out = obfuscate(src, config)
        with open(args.output, 'w', encoding='utf-8') as f: f.write(out)
        print(f"[+] Obfuscation complete. Output saved to {args.output}")
    except Exception as e: print(f"[-] Error: {e}")

if __name__ == '__main__': main()
