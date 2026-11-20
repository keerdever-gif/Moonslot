#!/usr/bin/env python3
# obfuscator.py — Luau VM obfuscator (Anti-Tamper 1x VM, User Script 18x VM)
import re
import random
import argparse

# ═══════════════════════════════════════════════════════════════════════════
# 1. WATERMARK Y ANTI-TAMPER
# ═══════════════════════════════════════════════════════════════════════════
HEADER = '''--[[
  Protected by Moonslot
  Unauthorized reproduction or distribution is prohibited.
]]'''

ANTI_TAMPER_CORE = r'''
local __at_code, __at_text = nil, nil
local __R = {
    ["0x02"]="HOOKFUNCTION_SANITY_HOOK_RETURN_MISMATCH", ["0x03"]="HOOKFUNCTION_SANITY_RESTORE_RETURN_MISMATCH",
    ["0x04"]="HOOKFUNCTION_SANITY_POINTER_MISMATCH", ["0x05"]="HOOKFUNCTION_SANITY_REHOOK_RETURN_MISMATCH",
    ["0x07"]="CRITICAL_FUNCTION_HOOKED_BOOT", ["0x09"]="CRITICAL_FUNCTION_HOOKED_RUNTIME",
}
local function __at_isHooked(fn)
    if type(fn) ~= "function" then return false end
    if type(isfunctionhooked) ~= "function" then return false end
    local ok, v = pcall(isfunctionhooked, fn)
    return ok and v == true
end
local function __at_checkCritical()
    -- Solo dispara si isfunctionhooked CONFIRMA que pcall o rawget están hookeados
    if __at_isHooked(pcall) then return "0x07" end
    if __at_isHooked(rawget) then return "0x07" end
    if __at_isHooked(rawset) then return "0x07" end
    if __at_isHooked(setmetatable) then return "0x07" end
    return nil
end
local function __at_checkHooks()
    -- Solo dispara si hookfunction/restorefunction están claramente rotos
    if type(hookfunction) ~= "function" then return nil end
    if type(restorefunction) ~= "function" then return nil end
    local function probe() return 1 end
    local ok, ret = pcall(restorefunction, probe)
    if not ok then return "0x03" end
    if ret ~= nil and type(ret) ~= "function" then return "0x03" end
    return nil
end
local function __at_run()
    local ok, code = pcall(__at_checkCritical)
    if ok and code then return code, __R[code] or "TAMPER" end
    ok, code = pcall(__at_checkHooks)
    if ok and code then return code, __R[code] or "TAMPER" end
    return nil, nil
end
__at_code, __at_text = __at_run()

if __at_code then
    local msg = "detect body go away"
    -- Triple canal visible en TODOS los ejecutores y en la consola de Roblox
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
    -- Freeze CON YIELD (evita el sandbox execution limit)
    while true do
        local ok = pcall(function()
            if type(task) == "table" and type(task.wait) == "function" then
                task.wait(1)
            elseif type(wait) == "function" then
                wait(1)
            else
                return false
            end
            return true
        end)
        if not ok then break end
    end
    error(msg, 0)
end
'''

# ═══════════════════════════════════════════════════════════════════════════
# 2. FORMAT LUA (Compresión sin romper strings)
# ═══════════════════════════════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════════════════════════════
# 3. SEAK OBFUSCATOR CORE
# ═══════════════════════════════════════════════════════════════════════════
_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"

def randomName() -> str:
    return "_" + "".join(random.choice(_BASE36) for _ in range(6)) + str(random.randint(0, 999))

def generateSingleJunkLine() -> str:
    r = random.random()
    if r < 0.2: return f"local {randomName()}={random.randint(0, 998)} "
    elif r < 0.35: return f"local {randomName()}=\"{random.randint(0, 254)}\" "
    elif r < 0.5: return f"if not(1==1) then local x=1 end "
    elif r < 0.7: return f'if type(nil)=="number" then while true do local {randomName()}=1 end end '
    elif r < 0.85: return f'do local {randomName()}={{}} {randomName()}["_"]=1 {randomName()}=nil end '
    else: return 'if type(math.pi)=="string" then while true do end end '

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

def runtimeString(s: str) -> str:
    return '"' + "".join(f"\\{ord(c):03d}" for c in s) + '"'

def buildTrueVM(payloadStr: str) -> str:
    STACK, KEY, ORDER, POOL, B_TABLE = randomName(), randomName(), randomName(), randomName(), randomName()
    seed = random.randint(50, 249)
    
    # Buffer de 256 caracteres para evitar bugs de string.char en LUNR
    vmCore = f"local {B_TABLE}={{}} for i=0,255 do local ok,r=pcall(string.char,i) if ok then {B_TABLE}[i]=r else {B_TABLE}[i]=string.char({{i}}) end end "
    vmCore += f"local {POOL}={{}} local {STACK}={{}} local {KEY}={seed} "
    
    chunkSize = 30
    realChunks = [payloadStr[i:i + chunkSize] for i in range(0, len(payloadStr), chunkSize)]
    realOrder = []
    
    # Multiplicador de 1.2x para mantener el tamaño bajo
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
    
    ASSERT = f'getgenv()[{runtimeString("assert")}]'
    LOADSTRING = f'getgenv()[{runtimeString("loadstring")}]'
    
    # Chunk name "=" oculta el source en los tracebacks
    vmCore += f"{ASSERT}({LOADSTRING}(_e, \"=\"))() "
    return vmCore

def buildSingleVM(innerCode: str, handlerCount: int) -> str:
    DISPATCH = randomName()
    out = f"local {DISPATCH}={{}} "
    realIdx = random.randint(0, handlerCount - 1)
    for i in range(handlerCount):
        if i == realIdx:
            out += f"{DISPATCH}[{i+1}]=function(lM) {generateSingleJunkLine()}{generateSingleJunkLine()} {innerCode} end "
        else:
            out += f"{DISPATCH}[{i+1}]=function(lM) {generateSingleJunkLine()} return nil end "
    execBlocks = [f"{DISPATCH}[{i+1}]({{}})" for i in range(handlerCount)]
    out += applyCFF(execBlocks)
    return out

def build1xVM(payloadStr: str) -> str:
    vm = buildTrueVM(payloadStr)
    vm = buildSingleVM(vm, random.randint(3, 4))
    return vm

def build18xVM(payloadStr: str) -> str:
    vm = buildTrueVM(payloadStr)
    for _ in range(18):
        vm = buildSingleVM(vm, random.randint(3, 4))
    return vm

def buildAntiEnvProtection():
    # Anti-Env Logger: Solo salta si la propiedad falla 3 veces seguidas (bloqueo real)
    antiEnvCode = """pcall(function() local p=game and game.Players and game.Players.LocalPlayer if not p then return end local o=pcall(function() return p.CameraMinZoomDistance end) if not o then return end local fails=0 for i=1,3 do local ok=pcall(function() p.CameraMinZoomDistance=-5 end) if not ok then fails=fails+1 end end if fails>=3 then pcall(function() local LS=game:GetService("LogService") if LS and LS.LogMessage then LS:LogMessage(3,"environment logger detected") end end) end end)"""
    fragSize = 4 + random.randint(0, 2)
    fragments = [antiEnvCode[i:i + fragSize] for i in range(0, len(antiEnvCode), fragSize)]
    tableName = randomName()
    fragmentLines = [f"{tableName}[#{tableName}+1] = \"{''.join(f'\\{ord(c):03d}' for c in frag)}\"" for frag in fragments]
    initLine = f"local {tableName} = {{}}"
    reconstructLine = f"local _reco = table.concat({tableName}); assert(loadstring(_reco, \"=\"))();"
    return initLine, fragmentLines, reconstructLine

def getExtraProtections() -> str:
    # Checks ligeros que no dan falsos positivos
    return """
pcall(function()
    if math.pi < 3.14 or math.pi > 3.15 then error("math corrupted") end
    if type(tostring) ~= "function" then error("tostring missing") end
    if type(pcall) ~= "function" then error("pcall missing") end
    if string.len("a") ~= 1 then error("string.len broken") end
    if math.floor(-1/10) ~= -1 then error("math.floor broken") end
end)
"""

# ═══════════════════════════════════════════════════════════════════════════
# 4. ORQUESTADOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════
def obfuscate(sourceCode: str, seed: int = 0) -> str:
    if not sourceCode:
        return '--ERROR'
    random.seed(seed)
    
    # 1. Preparar Anti-Env y Anti-Debug
    initLine, fragmentLines, reconstructLine = buildAntiEnvProtection()
    antiEnvCode = "\n".join([initLine] + fragmentLines + [reconstructLine])
    
    antiDebug = "local _t=tick() for _=1,150000 do end if tick()-_t>5.0 then while true do task.wait(1) end end "
    extraProts = getExtraProtections()
    
    # 2. Unir todo el bloque de protección
    protection_payload = (
        "local __run_at = function()\n"
        + ANTI_TAMPER_CORE.strip() + "\n"
        + "end\n"
        + "pcall(__run_at)\n"
        + antiEnvCode + "\n"
        + antiDebug + "\n"
        + extraProts
    )

    # 3. Ofuscar Protección (1 VM ligera para que no pese)
    final_protection = build1xVM(protection_payload)

    # 4. Ofuscar Script del Usuario (18 VM)
    isLoadstringRegex = re.compile(
        r'loadstring\s*\(\s*game\s*:\s*HttpGet\s*\(\s*["\']([^"\']+)["\']\s*\)\s*\)\s*\(\s*\)',
        re.IGNORECASE)
    match = isLoadstringRegex.search(sourceCode)
    payloadToProtect = match.group(1) if match else sourceCode
    
    final_user_script = build18xVM(payloadToProtect)

    # 5. Ensamblar
    final_code = (
        f"{HEADER}\n\n"
        f"{final_protection}\n"
        f"{final_user_script}"
    )
    return format_lua_output(final_code, max_line=120)

# ═══════════════════════════════════════════════════════════════════════════
# 5. CLI
# ═══════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--output', default='obfuscated.lua')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--min-size', type=int, default=23000)
    args = ap.parse_args()
    with open(args.input, encoding='utf-8') as f:
        src = f.read()
    out = obfuscate(src, seed=args.seed)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(out)

if __name__ == '__main__':
    main()
