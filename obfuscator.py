import re
import random
import argparse

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

def format_lua_output(code, max_line=120):
    out, buf, i, n = [], [], 0, len(code)
    line_len = 0
    st = 'normal'; lstr_close = None; lcom_close = None
    def flush():
        nonlocal buf, line_len
        if buf:
            line = ''.join(buf).rstrip()
            if line: out.append(line)
            buf = []; line_len = 0
    while i < n:
        c = code[i]
        if st == 'dq':
            buf.append(c); line_len += 1
            if c == '\\' and i + 1 < n: buf.append(code[i+1]); line_len += 1; i += 2; continue
            if c == '"': st = 'normal'
            i += 1; continue
        if st == 'sq':
            buf.append(c); line_len += 1
            if c == '\\' and i + 1 < n: buf.append(code[i+1]); line_len += 1; i += 2; continue
            if c == "'": st = 'normal'
            i += 1; continue
        if st == 'lstr':
            if code.startswith(lstr_close, i):
                buf.append(lstr_close); line_len += len(lstr_close); i += len(lstr_close); st = 'normal'; continue
            buf.append(c); line_len += 1
            if c == '\n': flush()
            i += 1; continue
        if st == 'lcom':
            if code.startswith(lcom_close, i):
                buf.append(lcom_close); line_len += len(lcom_close); i += len(lcom_close); st = 'normal'; continue
            buf.append(c); line_len += 1
            if c == '\n': flush()
            i += 1; continue
        if st == 'com':
            buf.append(c); line_len += 1
            if c == '\n': flush(); st = 'normal'
            i += 1; continue
        if code.startswith('--', i):
            m = re.match(r'--\[(=*)\[', code[i:])
            if m:
                eq = m.group(1); lcom_close = ']' + eq + ']'
                tok = code[i:i+3+len(eq)]; buf.append(tok); line_len += len(tok); i += len(tok); st = 'lcom'; continue
            buf.append('--'); line_len += 2; i += 2; st = 'com'; continue
        if c == '[':
            m = re.match(r'\[(=*)\[', code[i:])
            if m:
                eq = m.group(1); lstr_close = ']' + eq + ']'
                tok = code[i:i+2+len(eq)]; buf.append(tok); line_len += len(tok); i += len(tok); st = 'lstr'; continue
        if c == '"': st = 'dq'; buf.append(c); line_len += 1; i += 1; continue
        if c == "'": st = 'sq'; buf.append(c); line_len += 1; i += 1; continue
        buf.append(c); line_len += 1
        if c == '\n': flush(); i += 1; continue
        if line_len >= max_line:
            if c in ';,}': flush(); i += 1; continue
            if c == ' ': flush(); i += 1; continue
            s = ''.join(buf)
            idx = -1
            for k in range(len(s)-1, -1, -1):
                if s[k] in ' ,;': idx = k; break
            if idx > 0 and idx > len(s) * 0.5:
                out.append(s[:idx].rstrip()); buf = [s[idx:].lstrip()]; line_len = len(buf[0]); i += 1; continue
        i += 1
    flush()
    return '\n'.join(out)

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

def buildTrueVM(payloadStr: str) -> str:
    STACK, KEY, ORDER, POOL, B_TABLE = randomName(), randomName(), randomName(), randomName(), randomName()
    seed = random.randint(50, 249)
    vmCore = f"local _opcodes={{'ADD','SUB','MOV','JMP','CALL'}} local _ = _opcodes[math.random(1,5)] "
    vmCore += f"local {B_TABLE}={{}} for i=0,255 do local ok,r=pcall(string.char,i) if ok then {B_TABLE}[i]=r else {B_TABLE}[i]=string.char({{i}}) end end "
    vmCore += f"local {POOL}={{}} local {STACK}={{}} local {KEY}={seed} "
    chunkSize = 30
    realChunks = [payloadStr[i:i + chunkSize] for i in range(0, len(payloadStr), chunkSize)]
    realOrder = []
    totalChunks = int(len(realChunks) * 1.2) if len(realChunks) > 1 else 1
    if totalChunks < len(realChunks): totalChunks = len(realChunks)
    currentReal, globalIndex = 0, 0
    for i in range(1, totalChunks + 1):
        if currentReal < len(realChunks) and (random.random() > 0.4 or (totalChunks - i) == (len(realChunks) - currentReal)):
            realOrder.append(i)
            chunk = realChunks[currentReal]
            encryptedBytes = []
            for j in range(len(chunk)):
                enc = ord(chunk[j]) ^ ((seed + globalIndex) & 0xFF)
                encryptedBytes.append(str(enc))
                globalIndex += 1
            vmCore += f"{POOL}[{i}]={{{','.join(encryptedBytes)}}} "
            currentReal += 1
        else:
            fakeBytes = [str(random.randint(0, 254)) for _ in range(random.randint(5, 15))]
            vmCore += f"{POOL}[{i}]={{{','.join(fakeBytes)}}} "
    vmCore += f"local {ORDER}={{{','.join(str(n) for n in realOrder)}}} "
    idxVar, byteVar = randomName(), randomName()
    vmCore += f"local _gIdx=0 for _, {idxVar} in ipairs({ORDER}) do for _, {byteVar} in ipairs({POOL}[{idxVar}]) do "
    vmCore += f"local b = math.floor(bit32.bxor({byteVar}, ({KEY} + _gIdx) % 256)) % 256 "
    vmCore += f"table.insert({STACK}, {B_TABLE}[b]) _gIdx=_gIdx+1 end end "
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
        nested = f"(function() pcall(function() {nested} end) end)()"
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
# NUEVO: minificado + empaquetado SOLO con VM (sin _soup)
# ============================================================

def minify_payload(code: str) -> str:
    """Minifica sin romper strings/comentarios: une líneas y colapsa espacios seguros."""
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
    """Anti-tamper empaquetado SOLO con VM (sin _soup, sin tablas de bytes, sin strings gigantes)."""
    mini = minify_payload(code_str)
    packed = build18xVM(mini)              # VM real + 18 capas de VM
    packed = buildStackObfuscation(packed) # capas de pcall/anon
    return packed

# ============================================================

def obfuscate(sourceCode: str, seed: int = 0) -> str:
    if not sourceCode:
        return '--ERROR'
    random.seed(seed)

    antiDebug = "local _t=tick() for _=1,150000 do end if tick()-_t>5.0 then while true do task.wait(0.1) end end "
    extraProts = getExtraProtections()
    protection_payload = antiDebug + "\n" + extraProts + "\n" + ANTI_TAMPER_CORE

    # ANTES: anti_tamper_final = build_fragmented_payload(protection_payload, 100)
    # AHORA: minificado + ofuscado con la propia VM, sin _soup ni bytes/octales
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
    return format_lua_output(final_code, max_line=120)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--output', default='obfuscated.lua')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--min-size', type=int, default=23000) # compatibilidad

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
