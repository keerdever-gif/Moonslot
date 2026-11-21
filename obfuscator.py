import re
import random
import argparse
import base64

HEADER = '''--[[
  Protected by Moonslot - Polymorphic VM Obfuscation
  Unauthorized reproduction or distribution is prohibited.
]]\n'''

# ── ANTI-TAMPER DISTRIBUIDO Y DEFENSIVO ───────────────────────────────────
ANTI_TAMPER_CORE = r'''
local function _get_integrity_offset()
    local offset = 0
    local check_fns = {pcall, type, tostring, next, pairs, ipairs, rawget, rawset, setmetatable}
    
    -- 1. Verificación de integridad de funciones nativas
    if type(bit32) ~= "table" or type(bit32.bxor) ~= "function" then offset = offset + 1 end
    if type(table.concat) ~= "function" then offset = offset + 1 end
    
    -- 2. Verificación de entorno y debug
    if type(debug) == "table" then
        if type(debug.getinfo) == "function" then
            local ok, info = pcall(debug.getinfo, 1)
            if ok and info and info.what == "C" then offset = offset + 1 end
        end
        if type(debug.gethook) == "function" then
            local ok, hook = pcall(debug.gethook)
            if ok and hook ~= nil then offset = offset + 1 end
        end
    end
    
    -- 3. Detección de hooks en entorno
    local env = (getgenv and type(getgenv) == "function") and getgenv() or _G
    if env then
        local hooked = env["isfunctionhooked"] or env["is_function_hooked"]
        if type(hooked) == "function" then
            for _, fn in ipairs(check_fns) do
                local ok, res = pcall(hooked, fn)
                if ok and res == true then offset = offset + 1 end
            end
        end
        for k, v in pairs(env) do
            local ks = tostring(k)
            if type(v) == "function" and (string.find(ks, "hook") or string.find(ks, "detour") or string.find(ks, "logger")) then
                offset = offset + 1
            end
        end
    end
    
    return offset
end
'''

_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"

def randomName() -> str:
    return "_" + "".join(random.choice(_BASE36) for _ in range(6)) + str(random.randint(0, 9999))

# ── VARIABLES OPACAS DETERMINISTAS ────────────────────────────────────────
def generate_opaque_var(var_name) -> str:
    # Siempre devuelve 1, pero usando operaciones que parecen complejas
    r = random.randint(1, 100)
    op = random.choice(['bxor', 'band', 'bor'])
    if op == 'bxor':
        expr = f"bit32.bxor({r}, {r}) + 1"
    elif op == 'band':
        expr = f"bit32.band({r}, {r}) + 1"
    else:
        expr = f"bit32.bor({r}, {r}) - {r} + 1" 
    return f"local {var_name} = {expr} "

def generate_opaque_predicate() -> str:
    # Siempre devuelve true
    r = random.randint(1, 100)
    return f"(bit32.bxor({r}, {r}) == 0)"

def generateSingleJunkLine() -> str:
    r = random.random()
    pred = generate_opaque_predicate()
    v = randomName()
    if r < 0.2: return f"if {pred} then local {v}={random.randint(0, 998)} end "
    elif r < 0.4: return f"local {v}={{}} for i=1,50 do {v}[i]=string.rep('x',10) end "
    elif r < 0.6: return f"do local {v} = setmetatable({{}}, {{__index=function() return math.random() end, __metatable='locked'}}) end "
    elif r < 0.8: return f"pcall(function() if {pred} then return string.len('random') end end) "
    else: return f"local {v}=math.floor(math.random({random.randint(1,50)}, 500)) "

# ── TOKENIZADOR Y RENOMBRADOR SEGURO ──────────────────────────────────────
def tokenize_lua(code: str):
    tokens = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if c in '"\'':
            quote = c
            j = i + 1
            while j < n and code[j] != quote:
                if code[j] == '\\': j += 1
                j += 1
            tokens.append(code[i:j+1])
            i = j + 1
        elif c == '[':
            m = re.match(r'\[(=*)\[', code[i:])
            if m:
                eq = m.group(1)
                close = ']' + eq + ']'
                j = code.find(close, i)
                if j != -1:
                    tokens.append(code[i:j+len(close)])
                    i = j + len(close)
                    continue
            tokens.append(c)
            i += 1
        elif c.isspace():
            i += 1
        elif c.isalnum() or c == '_':
            j = i
            while j < n and (code[j].isalnum() or code[j] == '_'):
                j += 1
            tokens.append(code[i:j])
            i = j
        else:
            tokens.append(c)
            i += 1
    return tokens

def obfuscate_identifiers(code: str) -> str:
    tokens = tokenize_lua(code)
    keywords = {'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function', 'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then', 'true', 'until', 'while', 'pcall', 'type', 'math', 'string', 'table', 'bit32', 'game', 'task', 'loadstring', 'getfenv', 'getgenv', 'setfenv', 'debug', 'ipairs', 'pairs', 'next', 'tostring', 'rawget', 'rawset', 'setmetatable', 'getmetatable', 'print', 'warn', 'error', 'assert', 'select', 'tonumber', 'os', 'wait', 'tick', 'spawn', 'delay', 'workspace', 'Workspace', 'script'}
    
    # 1. Identificar variables locales
    local_vars = set()
    for idx, tok in enumerate(tokens):
        if tok == 'local':
            j = idx + 1
            if j < len(tokens) and tokens[j] == 'function':
                j += 1
            while j < len(tokens) and (tokens[j].isalnum() or tokens[j] == '_' or tokens[j] == ','):
                if tokens[j] != ',':
                    if tokens[j] not in keywords and (tokens[j][0].isalpha() or tokens[j][0] == '_'):
                        local_vars.add(tokens[j])
                j += 1
                if j < len(tokens) and tokens[j] == '=':
                    break
                if j < len(tokens) and tokens[j] == 'then': 
                    break
                    
    # 2. Mapa consistente
    mapping = {var: randomName() for var in local_vars}
    
    # 3. Aplicar reemplazo seguro con Lookbehind (evita .propiedades y :métodos)
    for old, new in mapping.items():
        code = re.sub(rf'(?<![\w\.:]){old}\b', new, code)
        
    return code

def minify_payload(code):
    code = re.sub(r'--\[\[.*?\]\]', '', code, flags=re.DOTALL)
    code = re.sub(r'--[^\n]*', '', code)
    tokens = tokenize_lua(code)
    out = []
    for idx, tok in enumerate(tokens):
        out.append(tok)
        if idx < len(tokens) - 1:
            nxt = tokens[idx+1]
            if (tok[-1].isalnum() or tok[-1] == '_') and (nxt[0].isalnum() or nxt[0] == '_'):
                out.append(' ')
    return ''.join(out)

# ── CONSTRUCTORES DE VM POLIMÓRFICAS ──────────────────────────────────────
def build_vm_table_style(inner_code, config):
    store = randomName()
    mt = randomName()
    dispatch = randomName()
    
    op_vars = [randomName() for _ in range(config["opaque_vars"])]
    out = ""
    for ov in op_vars:
        out += generate_opaque_var(ov)
        
    out += f"local {store}={{}} local {mt}={{__index=function(t,k) return {store}[k] end, __metatable='locked'}} "
    out += f"local {dispatch}=setmetatable({{}},{mt}) "
    
    handler_count = random.randint(4, 7)
    real_idx = random.randint(1, handler_count)
    
    for i in range(1, handler_count + 1):
        if i == real_idx:
            out += f"{store}[{i}]=function(lM) {generateSingleJunkLine()}{generateSingleJunkLine()} {inner_code} end "
        else:
            out += f"{store}[{i}]=function(lM) {generateSingleJunkLine()} return nil end "
            
    cond_str = " and ".join([f"{ov} == 1" for ov in op_vars])
    if not cond_str:
        cond_str = "true"
        
    out += f"local _state=1 while _state > 0 do "
    out += f"if _state==1 and {cond_str} and {generate_opaque_predicate()} then {dispatch}[{real_idx}]({{}}) _state=0 end "
    out += "end "
    return out

def build_vm_ifchain_style(inner_code, config):
    out = ""
    state_var = randomName()
    
    branches = [random.randint(100, 999) for _ in range(random.randint(3, 5))]
    real_branch = random.choice(branches)
    initial_state = real_branch
    
    op_vars = [randomName() for _ in range(config["opaque_vars"])]
    for ov in op_vars:
        out += generate_opaque_var(ov)
        
    out += f"local {state_var} = {initial_state} "
    out += f"while {state_var} ~= 0 do "
    
    cond_str = " and ".join([f"{ov} == 1" for ov in op_vars])
    if not cond_str:
        cond_str = "true"
        
    for i, b in enumerate(branches):
        prefix = "if" if i == 0 else "elseif"
        if b == real_branch:
            out += f"{prefix} {state_var} == {b} and {cond_str} then {generateSingleJunkLine()} {inner_code} {state_var} = 0 "
        else:
            out += f"{prefix} {state_var} == {b} then {state_var} = {random.randint(0, 1)} "
            
    out += "else break end end "
    return out

def build_vm_cff_style(inner_code, config):
    var_s = randomName()
    out = f"local {var_s} = 10 "
    
    op_vars = [randomName() for _ in range(config["opaque_vars"])]
    for ov in op_vars:
        out += generate_opaque_var(ov)
        
    cond_str = " and ".join([f"{ov} == 1" for ov in op_vars])
    if not cond_str:
        cond_str = "true"
        
    out += f"repeat "
    out += f"if {var_s} == 10 and {cond_str} then {generateSingleJunkLine()} {inner_code} {var_s} = 20 "
    out += f"elseif {var_s} == 20 then {var_s} = 99 "
    out += f"else {var_s} = 99 end "
    out += f"until {var_s} == 99 "
    return out

def build_polymorphic_layer(inner_code, config):
    mode = config["polymorphic_mode"]
    if mode == "auto" or mode == "mixed":
        mode = random.choice(["table", "ifchain", "cff"])
        
    if mode == "table":
        return build_vm_table_style(inner_code, config)
    elif mode == "ifchain":
        return build_vm_ifchain_style(inner_code, config)
    else:
        return build_vm_cff_style(inner_code, config)

# ── NÚCLEO DE ENCRIPTACIÓN (BASE64 + ESTADO ACOPLADO) ─────────────────────
def generate_b64_soup(pool, idx, b64):
    pieces = [b64[i:i+8] for i in range(0, len(b64), 8)]
    pieces_table = ",".join(f"'{p}'" for p in pieces)
    r = random.random()
    if r < 0.25: return f"{pool}[{idx}]=table.concat({{{pieces_table}}})"
    elif r < 0.5:
        v = randomName()
        return f"do local {v}=table.concat({{{pieces_table}}}) {pool}[{idx}]={v} end"
    elif r < 0.75:
        return f"if {generate_opaque_predicate()} then {pool}[{idx}]=table.concat({{{pieces_table}}}) end"
    else:
        return f"{generateSingleJunkLine()} {pool}[{idx}]=string.format('%s',table.concat({{{pieces_table}}}))"

def buildTrueVM(payloadStr: str, config) -> str:
    STACK, KEY1, KEY2, ORDER, POOL, B_TABLE = randomName(), randomName(), randomName(), randomName(), randomName(), randomName()
    seed1 = random.randint(10, 250)
    seed2 = random.randint(20, 240)
    B64_TABLE = randomName()
    DECODE_FUNC = randomName()
    
    vmCore = f"{ANTI_TAMPER_CORE}\n"
    vmCore += f"local _offset = _get_integrity_offset() "
    vmCore += f"local {B_TABLE}={{}} for i=0,255 do local ok,r=pcall(string.char,i) if ok then {B_TABLE}[i]=r else {B_TABLE}[i]=string.char({{i}}) end end "
    vmCore += f"local {STACK}={{}} local {KEY1}={seed1} + _offset local {KEY2}={seed2} - (_offset * 2) "
    
    # Búsqueda dinámica y segura de Load
    vmCore += "local _env = (getgenv and type(getgenv)=='function') and getgenv() or _G "
    vmCore += "local _ls = nil "
    vmCore += f"local _ls_name = string.char({','.join(str(ord(c)) for c in 'loadstring')}) "
    vmCore += f"local _l_name = string.char({','.join(str(ord(c)) for c in 'load')}) "
    vmCore += "for _k, _v in pairs(_env) do "
    vmCore += "  if (_k == _ls_name or _k == _l_name) and type(_v) == 'function' then _ls = _v break end "
    vmCore += "end "
    vmCore += "if not _ls and type(_G) == 'table' then "
    vmCore += "  for _k, _v in pairs(_G) do "
    vmCore += "    if (_k == _ls_name or _k == _l_name) and type(_v) == 'function' then _ls = _v break end "
    vmCore += "  end "
    vmCore += "end "
    vmCore += "if not _ls and type(getfenv) == 'function' then "
    vmCore += "  local ok, fenv = pcall(getfenv) "
    vmCore += "  if ok and type(fenv) == 'table' then "
    vmCore += "    for _k, _v in pairs(fenv) do "
    vmCore += "      if (_k == _ls_name or _k == _l_name) and type(_v) == 'function' then _ls = _v break end "
    vmCore += "    end "
    vmCore += "  end "
    vmCore += "end "
    
    vmCore += f"local {B64_TABLE}='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/' "
    vmCore += f"local function {DECODE_FUNC}(data) local res={{}} local i=1 while i<=#data do "
    vmCore += f"local b1,b2,b3,b4=data:byte(i,i+3) "
    vmCore += f"local c1,c2,c3,c4={B64_TABLE}:find(string.char(b1),1,true),{B64_TABLE}:find(string.char(b2),1,true),{B64_TABLE}:find(string.char(b3),1,true),{B64_TABLE}:find(string.char(b4),1,true) "
    vmCore += f"c1,c2,c3,c4=c1-1,c2 and c2-1,c3 and c3-1,c4 and c4-1 "
    vmCore += f"local byte1=math.floor(c1*4+(c2 or 0)/16) "
    vmCore += f"local byte2=math.floor(((c2 or 0)%16)*16+(c3 or 0)/4) "
    vmCore += f"local byte3=math.floor(((c3 or 0)%4)*64+(c4 or 0)) "
    vmCore += f"table.insert(res,string.char(byte1)) "
    vmCore += f"if c3 then table.insert(res,string.char(byte2)) end if c4 then table.insert(res,string.char(byte3)) end "
    vmCore += f"i=i+4 end return table.concat(res) end "
    
    chunkSize = 40
    realChunks = [payloadStr[i:i + chunkSize] for i in range(0, len(payloadStr), chunkSize)]
    realOrder = []
    totalChunks = int(len(realChunks) * 1.3) if len(realChunks) > 1 else 1
    if totalChunks < len(realChunks): totalChunks = len(realChunks)
    currentReal = 0
    
    rot_state = seed1
    for i in range(1, totalChunks + 1):
        if currentReal < len(realChunks) and (random.random() > 0.3 or (totalChunks - i) == (len(realChunks) - currentReal)):
            realOrder.append(i)
            chunk = realChunks[currentReal]
            chunk_bytes = chunk.encode('utf-8')
            encryptedBytes = bytearray()
            for j in range(len(chunk_bytes)):
                rot_state = (rot_state * 31 + seed2) % 256
                enc_byte = chunk_bytes[j] ^ rot_state
                encryptedBytes.append(enc_byte)
                
            b64_str = base64.b64encode(encryptedBytes).decode('ascii')
            vmCore += generate_b64_soup(POOL, i, b64_str)
            currentReal += 1
        else:
            fake_bytes = bytes([random.randint(0, 255) for _ in range(random.randint(5, 25))])
            b64_fake = base64.b64encode(fake_bytes).decode('ascii')
            vmCore += generate_b64_soup(POOL, i, b64_fake)
            
    vmCore += f" local {ORDER}={{{','.join(str(n) for n in realOrder)}}} "
    idxVar, jVar = randomName(), randomName()
    vmCore += f"local _rot = {KEY1} "
    vmCore += f"for _,{idxVar} in ipairs({ORDER}) do "
    vmCore += f"local dec_chunk={DECODE_FUNC}({POOL}[{idxVar}]) "
    vmCore += f"for {jVar}=1,#dec_chunk do "
    vmCore += f"  _rot = (_rot * 31 + {KEY2}) % 256 "
    vmCore += f"  local b=dec_chunk:byte({jVar}) "
    vmCore += f"  local real_b=math.floor(bit32.bxor(b, _rot))%256 "
    vmCore += f"  table.insert({STACK},{B_TABLE}[real_b]) "
    vmCore += f"end end "
    vmCore += f"local _e=table.concat({STACK}) {STACK}=nil "
    
    # Sandbox de Ejecución
    vmCore += "local _sandbox = setmetatable({}, {__index = _env}) "
    vmCore += "if type(_ls) == 'function' then "
    vmCore += "  local _ok, _res = pcall(_ls, _e, '=') "
    vmCore += "  if _ok and _res then "
    vmCore += "    if type(setfenv) == 'function' then pcall(setfenv, _res, _sandbox) end "
    vmCore += "    pcall(_res) "
    vmCore += "  end "
    vmCore += "end "
    vmCore += "_e = nil "
    return vmCore

# ── ORQUESTADOR PRINCIPAL ─────────────────────────────────────────────────
def getExtraProtections() -> str:
    return """
pcall(function()
    local t = setmetatable({}, {__metatable = "locked"})
    if getmetatable(t) ~= "locked" then error("mt") end
    if type(_G) ~= "table" then error("g") end
    if type(os) == "table" and type(os.clock) == "function" then
        local c = os.clock()
        if type(c) ~= "number" then error("clock") end
    end
end)
"""

def obfuscate(sourceCode: str, config: dict) -> str:
    if not sourceCode:
        return '--ERROR'
    
    random.seed(config["seed"])

    # 1. Procesar el código del usuario
    minified_user_code = minify_payload(sourceCode)
    obfuscated_user_code = obfuscate_identifiers(minified_user_code)
    
    # 2. Empaquetar en el Multi-VM Polimórfico
    final_user_script = buildTrueVM(obfuscated_user_code, config)
    for i in range(config["vm_layers"]):
        final_user_script = build_polymorphic_layer(final_user_script, config)
        
    final_user_script = f"(function() pcall(function() {final_user_script} end) end)()"

    # 3. Empaquetar el Anti-Tamper
    protection_payload = minify_payload(getExtraProtections())
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
    parser = argparse.ArgumentParser(description="Moonslot - Polymorphic Lua Obfuscator")
    parser.add_argument('input', help="Archivo de entrada Lua")
    parser.add_argument('-o', '--output', default='obfuscated.lua', help="Archivo de salida")
    parser.add_argument('--seed', type=int, default=0, help="Semilla para reproducibilidad")
    
    parser.add_argument('--vm-layers', type=int, default=5, help="Número de capas de VM para el script")
    parser.add_argument('--anti-tamper-layers', type=int, default=3, help="Capas de VM para el Anti-Tamper")
    parser.add_argument('--opaque-vars', type=int, default=2, help="Cantidad de variables opacas por capa")
    parser.add_argument('--polymorphic-mode', choices=['auto', 'table', 'ifchain', 'cff', 'mixed'], default='auto', help="Estilo de despacho de VM")

    args, unknown = parser.parse_known_args()

    config = {
        "seed": args.seed,
        "vm_layers": args.vm_layers,
        "anti_tamper_layers": args.anti_tamper_layers,
        "opaque_vars": args.opaque_vars,
        "polymorphic_mode": args.polymorphic_mode
    }

    try:
        with open(args.input, encoding='utf-8') as f:
            src = f.read()
        out = obfuscate(src, config)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(out)
        print(f"[+] Obfuscation complete. Output saved to {args.output}")
    except Exception as e:
        print(f"[-] Error: {e}")
        exit(1)

if __name__ == '__main__':
    main()
