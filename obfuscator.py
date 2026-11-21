import re
import random
import argparse
import base64

HEADER = '''--[[
  Protected by Moonslot - Extreme Obfuscation
  Unauthorized reproduction or distribution is prohibited.
]]'''

ANTI_TAMPER_CORE = r'''
local __at_code, __at_text = nil, nil
local _s = function(...) return table.concat({...}) end
local __R = setmetatable({}, {
    __index = function(t, k)
        local v = {
            ["0x07"] = _s("CRIT", "ICAL_FUN", "CTION_HOOK", "ED_BOOT"),
            ["0x09"] = _s("CRIT", "ICAL_FUN", "CTION_HOOK", "ED_RUNTIME"),
            ["0x50"] = _s("ENV_LOG", "GER_HOOK_", "DETECTED"),
        }
        return v[k]
    end
})
local function __is_executor()
    local e1 = _s("ident", "ifyexec", "utor")
    local e2 = _s("getg", "env")
    local ok, exec = pcall(function() return _G[e1] and _G[e1]() end)
    if ok and exec and exec ~= _s("Unk", "nown") then return true end
    if type(_G[e2]) == "function" or type(_G[e2]) == "table" then return true end
    if type(_G[_s("getf", "env")]) == "function" then
        local ok2, env = pcall(_G[_s("getf", "env")])
        if ok2 and env and (env.script or env.loadstring) then return true end
    end
    if type(_G[_s("s", "yn")]) == "table" or type(_G[_s("se", "cure_call")]) == "function" then return true end
    return false
end
local function __at_isHooked(fn)
    if type(fn) ~= "function" then return false end
    local ishook = _G[_s("isfunc", "tionhoo", "ked")]
    if type(ishook) ~= "function" then return false end
    local ok, v = pcall(ishook, fn)
    return ok and v == true
end
local function __at_checkCritical()
    if __is_executor() then return nil end 
    local ishook = _G[_s("isfunc", "tionhoo", "ked")]
    if type(ishook) ~= "function" then return nil end
    local count = 0
    if __at_isHooked(pcall) then count = count + 1 end
    if __at_isHooked(rawget) then count = count + 1 end
    if __at_isHooked(rawset) then count = count + 1 end
    if __at_isHooked(setmetatable) then count = count + 1 end
    if count >= 2 then return "0x07" end
    return nil
end
local function __at_checkEnvLogger()
    local tampered = false
    pcall(function()
        local p = game and game.Players and game.Players.LocalPlayer
        if not p then return end
        if math.floor(1.5) ~= 1 or math.ceil(1.5) ~= 2 then tampered = true end
        if string.len("abc") ~= 3 then tampered = true end
        if type(tostring) ~= "function" then tampered = true end
    end)
    if tampered then return "0x50" end
    return nil
end
local function __at_run()
    local ok, code = pcall(__at_checkCritical)
    if ok and code then return code, __R[code] or _s("TAM", "PER") end
    ok, code = pcall(__at_checkEnvLogger)
    if ok and code then return code, __R[code] or _s("TAM", "PER") end
    return nil, nil
end
__at_code, __at_text = __at_run()
if __at_code then
    local msg = _s("detect ", "body go ", "away")
    pcall(function() if type(warn) == "function" then warn(msg) end end)
    pcall(function() if type(print) == "function" then print(msg) end end)
    pcall(function()
        if type(game) == "userdata" or type(game) == "table" then
            local ok, LS = pcall(function() return game:GetService("LogService") end)
            if ok and LS and LS.LogMessage then
                pcall(function() LS:LogMessage(3, msg) end)
            end
        end
    end)
    while true do
        local ok = pcall(function()
            if type(task) == "table" and type(task.wait) == "function" then
                task.wait(0.1)
            elseif type(wait) == "function" then
                wait(0.1)
            else
                return false
            end
            return true
        end)
        if not ok then break end
    end
end
'''

_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"

def randomName() -> str:
    return "_" + "".join(random.choice(_BASE36) for _ in range(6)) + str(random.randint(0, 999))

def generateSingleJunkLine() -> str:
    r = random.random()
    if r < 0.15: return f"local {randomName()}={random.randint(0, 998)} "
    elif r < 0.3: return f"local {randomName()}=\"{random.randint(0, 254)}\" "
    elif r < 0.4: return f"if not(1==1) then local x=1 end "
    elif r < 0.55: return f'if type(nil)=="number" then while true do local {randomName()}=1 end end '
    elif r < 0.7: 
        v = randomName()
        return f'do local {v}={{}} {v}["_"]=1 {v}=nil end '
    elif r < 0.8: return 'if type(math.pi)=="string" then while true do end end '
    elif r < 0.9: return 'if debug and debug.sethook then pcall(function() debug.sethook() end) end '
    else: 
        return f'local {randomName()}={{}} for i=1,500 do {randomName()}[i]=string.rep("x",50) end {randomName()}=nil pcall(collectgarbage) '

def generate_soup_junk() -> str:
    r = random.random()
    if r < 0.2: return "local _x = math.random(1,100) "
    elif r < 0.4: return "if _G then _G._dummy = 1 end "
    elif r < 0.6: return "for _i=1,5 do local _y = _i * 2 end "
    elif r < 0.8: return "pcall(function() return string.rep('a', 10) end) "
    else: return "local _t = setmetatable({}, {__index = function() return 1 end}) "

def obfuscate_identifiers(code: str) -> str:
    code = re.sub(r'\bt\(k\)', f'{randomName()}({randomName()})', code)
    code = re.sub(r'\b(lM|t|k)\b', lambda m: randomName() if m.group(0) in ('lM', 't', 'k') else m.group(0), code)
    local_vars = re.findall(r'\blocal\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
    for var in set(local_vars):
        if var not in ['function', 'pcall', 'type', 'math', 'string', 'table', 'bit32', 'game', 'task']:
            new_var = randomName()
            code = re.sub(rf'\b{var}\b', new_var, code)
    return code

def minify_payload(code: str) -> str:
    out = []
    buf = []
    i, n = 0, len(code)
    st = 'normal'
    close = None

    def flush():
        if buf:
            line = ''.join(buf).strip()
            if line:
                out.append(line)
            buf.clear()

    while i < n:
        c = code[i]
        if st in ('dq', 'sq'):
            buf.append(c)
            if c == '\\' and i + 1 < n:
                buf.append(code[i+1]); i += 2; continue
            if (st == 'dq' and c == '"') or (st == 'sq' and c == "'"):
                st = 'normal'
            i += 1; continue
        if st in ('lstr', 'lcom'):
            if code.startswith(close, i):
                buf.append(close); i += len(close); st = 'normal'; continue
            buf.append(c)
            if c == '\n':
                flush()
            i += 1; continue
        if st == 'com':
            if c == '\n':
                flush(); st = 'normal'; i += 1; continue
            i += 1; continue
        if code.startswith('--', i):
            m = re.match(r'--\[(=*)\[', code[i:])
            if m:
                eq = m.group(1); close = ']' + eq + ']'
                tok = code[i:i+3+len(eq)]; buf.append(tok); i += len(tok); st = 'lcom'; continue
            st = 'com'; i += 2; continue
        if c == '[':
            m = re.match(r'\[(=*)\[', code[i:])
            if m:
                eq = m.group(1); close = ']' + eq + ']'
                tok = code[i:i+2+len(eq)]; buf.append(tok); i += len(tok); st = 'lstr'; continue
        if c == '"': st = 'dq'; buf.append(c); i += 1; continue
        if c == "'": st = 'sq'; buf.append(c); i += 1; continue
        if c in ' \t\r':
            if buf and buf[-1] != ' ':
                buf.append(' ')
            i += 1; continue
        if c == '\n':
            buf.append(' '); i += 1; continue
        buf.append(c); i += 1
    flush()
    return ' '.join(out)

def build_vm_packed_payload(code_str: str) -> str:
    mini = minify_payload(code_str)
    mini = obfuscate_identifiers(mini)
    packed = build18xVM(mini)              
    packed = buildStackObfuscation(packed) 
    return packed

def applyCFF(blocks) -> str:
    stateVar = randomName()
    n = len(blocks)
    states = random.sample(range(1000, 99999), n + 1)
    lua = f"local {stateVar}={states[0]} while true do "
    for i, block in enumerate(blocks):
        prefix = "if" if i == 0 else "elseif"
        lua += f"{prefix} {stateVar}=={states[i]} then {block} {stateVar}={states[i+1]} "
    lua += f"elseif {stateVar}=={states[n]} then break end end "
    return lua

# ============================================================
# SOPA REAL: Fragmentación de Base64
# ============================================================

def generate_b64_soup(pool, idx, b64):
    # Partimos el Base64 en trozos de 10 caracteres
    pieces = [b64[i:i+10] for i in range(0, len(b64), 10)]
    # Creamos una concatenación con ".."
    concat_expr = " .. ".join(f"'{p}'" for p in pieces)
    
    r = random.random()
    if r < 0.15:
        return f"{pool}[{idx}] = {concat_expr} "
    elif r < 0.30:
        v = randomName()
        return f"do local {v} = {concat_expr} {pool}[{idx}] = {v} end "
    elif r < 0.45:
        v1, v2 = randomName(), randomName()
        return f"if type(tostring) == 'function' then local {v1} = {concat_expr} {pool}[{idx}] = {v1} end "
    elif r < 0.60:
        # Usar table.concat
        pieces_table = ", ".join(f"'{p}'" for p in pieces)
        return f"{generate_soup_junk()} {pool}[{idx}] = table.concat({{{pieces_table}}}) "
    elif r < 0.75:
        return f"{pool}[{idx}] = (function() return {concat_expr} end)() "
    elif r < 0.85:
        return f"for i=1,1 do local _x = {concat_expr} {pool}[{idx}] = _x end "
    else:
        return f"pcall(function() {pool}[{idx}] = {concat_expr} end) "

def buildTrueVM(payloadStr: str) -> str:
    STACK, KEY, ORDER, POOL, B_TABLE = randomName(), randomName(), randomName(), randomName(), randomName()
    seed = random.randint(50, 249)
    
    B64_TABLE = randomName()
    DECODE_FUNC = randomName()
    
    vmCore = f"local _opcodes={{'ADD','SUB','MOV','JMP','CALL'}} local _ = _opcodes[math.random(1,5)] "
    vmCore += f"local {B_TABLE}={{}} for i=0,255 do local ok,r=pcall(string.char,i) if ok then {B_TABLE}[i]=r else {B_TABLE}[i]=string.char({{i}}) end end "
    vmCore += f"local {STACK}={{}} local {KEY}={seed} "
    
    vmCore += f"local {B64_TABLE} = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/' "
    vmCore += f"local function {DECODE_FUNC}(data) local res = {{}} local i = 1 while i <= #data do "
    vmCore += f"local b1, b2, b3, b4 = data:byte(i, i+3) "
    vmCore += f"local c1, c2, c3, c4 = {B64_TABLE}:find(string.char(b1), 1, true), {B64_TABLE}:find(string.char(b2), 1, true), {B64_TABLE}:find(string.char(b3), 1, true), {B64_TABLE}:find(string.char(b4), 1, true) "
    vmCore += f"c1, c2, c3, c4 = c1 - 1, c2 and c2 - 1, c3 and c3 - 1, c4 and c4 - 1 "
    vmCore += f"local byte1 = math.floor(c1 * 4 + (c2 or 0) / 16) "
    vmCore += f"local byte2 = math.floor(((c2 or 0) % 16) * 16 + (c3 or 0) / 4) "
    vmCore += f"local byte3 = math.floor(((c3 or 0) % 4) * 64 + (c4 or 0)) "
    vmCore += f"table.insert(res, string.char(byte1)) "
    vmCore += f"if c3 then table.insert(res, string.char(byte2)) end "
    vmCore += f"if c4 then table.insert(res, string.char(byte3)) end "
    vmCore += f"i = i + 4 end return table.concat(res) end "
    
    chunkSize = 50
    realChunks = [payloadStr[i:i + chunkSize] for i in range(0, len(payloadStr), chunkSize)]
    realOrder = []
    totalChunks = int(len(realChunks) * 1.2) if len(realChunks) > 1 else 1
    if totalChunks < len(realChunks): totalChunks = len(realChunks)
    currentReal, globalIndex = 0, 0
    
    for i in range(1, totalChunks + 1):
        if currentReal < len(realChunks) and (random.random() > 0.4 or (totalChunks - i) == (len(realChunks) - currentReal)):
            realOrder.append(i)
            chunk = realChunks[currentReal]
            encryptedBytes = bytearray()
            for j in range(len(chunk)):
                encryptedBytes.append(ord(chunk[j]) ^ ((seed + globalIndex) & 0xFF))
                globalIndex += 1
            b64_str = base64.b64encode(encryptedBytes).decode('ascii')
            vmCore += generate_b64_soup(POOL, i, b64_str)
            currentReal += 1
        else:
            fake_bytes = bytes([random.randint(0, 255) for _ in range(random.randint(5, 20))])
            b64_fake = base64.b64encode(fake_bytes).decode('ascii')
            vmCore += generate_b64_soup(POOL, i, b64_fake)
            
    vmCore += f" local {ORDER}={{{','.join(str(n) for n in realOrder)}}} "
    idxVar = randomName()
    vmCore += f"local _gIdx=0 for _, {idxVar} in ipairs({ORDER}) do "
    vmCore += f"local dec_chunk = {DECODE_FUNC}({POOL}[{idxVar}]) "
    vmCore += f"for j=1, #dec_chunk do local b = dec_chunk:byte(j) "
    vmCore += f"local real_b = math.floor(bit32.bxor(b, ({KEY} + _gIdx) % 256)) % 256 "
    vmCore += f"table.insert({STACK}, {B_TABLE}[real_b]) _gIdx=_gIdx+1 end end "
    vmCore += f"local _e = table.concat({STACK}) {STACK}=nil "
    vmCore += "local _g = (getgenv and type(getgenv)=='function') and getgenv() or {} "
    vmCore += "local _loaders = {loadstring, load, _g.loadstring, (getfenv and getfenv().loadstring)} "
    vmCore += "local _ls = nil for _,l in ipairs(_loaders) do if type(l)=='function' then _ls=l break end end "
    vmCore += "if type(_ls) ~= 'function' then _ls = function(s) return function() end end end "
    vmCore += "local _ok, _res = pcall(_ls, _e, \"=\") "
    vmCore += "if not _ok then warn('Moonslot VM Error: '..tostring(_res)) else _res() end "
    return vmCore

def buildSingleVM(innerCode: str, handlerCount: int) -> str:
    DISPATCH = randomName()
    STORE = randomName()
    MT = randomName()
    out = f"local {STORE}={{}} local {MT}={{}} {MT}.__index=function(t,k) return {STORE}[k] end local {DISPATCH}=setmetatable({{}},{MT}) "
    realIdx = random.randint(0, handlerCount - 1)
    for i in range(handlerCount):
        if i == realIdx:
            out += f"{STORE}[{i+1}]=function(lM) {generateSingleJunkLine()}{generateSingleJunkLine()} {innerCode} end "
        else:
            out += f"{STORE}[{i+1}]=function(lM) {generateSingleJunkLine()} return nil end "
    execBlocks = [f"{DISPATCH}[{i+1}]({{}})" for i in range(handlerCount)]
    out += applyCFF(execBlocks)
    return out

def build18xVM(payloadStr: str) -> str:
    vm = buildTrueVM(payloadStr)
    for _ in range(18):
        vm = buildSingleVM(vm, random.randint(3, 4))
    return vm

def buildStackObfuscation(code: str) -> str:
    nested = code
    for _ in range(random.randint(2, 5)):
        nested = f"(function() pcall(function() {nested} end) end)(); "
    return nested

def getExtraProtections() -> str:
    return """
pcall(function()
    if math.pi < 3.14 or math.pi > 3.15 then error("math corrupted") end
    if type(tostring) ~= "function" then error("tostring missing") end
    if type(pcall) ~= "function" then error("pcall missing") end
    if string.len("a") ~= 1 then error("string.len broken") end
    if math.floor(-1/10) ~= -1 then error("math.floor broken") end
end)
"""

# ============================================================
# MINIFICADOR AGRESIVO (ELIMINA ESPACIOS GIGANTES)
# ============================================================

def true_minify(code):
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
            
    out = []
    for idx, tok in enumerate(tokens):
        out.append(tok)
        if idx < len(tokens) - 1:
            nxt = tokens[idx+1]
            if (tok[-1].isalnum() or tok[-1] == '_') and (nxt[0].isalnum() or nxt[0] == '_'):
                out.append(' ')
    return ''.join(out)

def obfuscate(sourceCode: str, seed: int = 0) -> str:
    if not sourceCode:
        return '--ERROR'
    random.seed(seed)

    antiDebug = "local _t=tick() for _=1,150000 do end if tick()-_t>5.0 then while true do task.wait(0.1) end end "
    extraProts = getExtraProtections()
    protection_payload = antiDebug + "\n" + extraProts + "\n" + ANTI_TAMPER_CORE

    anti_tamper_final = build_vm_packed_payload(protection_payload)

    isLoadstringRegex = re.compile(
        r'loadstring\s*\(\s*game\s*:\s*HttpGet\s*\(\s*["\']([^"\']+)["\']\s*\)\s*\)\s*\(\s*\)',
        re.IGNORECASE)
    match = isLoadstringRegex.search(sourceCode)
    payloadToProtect = match.group(1) if match else sourceCode

    final_user_script = build18xVM(payloadToProtect)
    final_user_script = buildStackObfuscation(final_user_script)

    final_code = (
        f"{HEADER}\n\n"
        f"-- Memory Confusion\n"
        f"local _mc = {{}} for i=1,3000 do _mc[i] = string.rep('X', 50) end _mc = nil pcall(collectgarbage)\n"
        f"{anti_tamper_final}\n"
        f"{final_user_script}"
    )
    
    # AHORA APLICAMOS LA MINIFICACIÓN AGRESIVA
    return true_minify(final_code)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--output', default='obfuscated.lua')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--min-size', type=int, default=23000)

    args, unknown = ap.parse_known_args()

    try:
        with open(args.input, encoding='utf-8') as f:
            src = f.read()
        out = obfuscate(src, seed=args.seed)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(out)
    except Exception as e:
        print(f"Error interno: {e}")
        exit(1)

if __name__ == '__main__':
    main()
