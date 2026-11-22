import re
import random
import argparse

HEADER = '''--[[
  Protected by Moonslot
  Unauthorized reproduction or distribution is prohibited.
]]'''

ANTI_TAMPER_CORE = r'''
local __at_code, __at_text = nil, nil
local __R = {
    ["0x07"]="CRITICAL_FUNCTION_HOOKED_BOOT", ["0x09"]="CRITICAL_FUNCTION_HOOKED_RUNTIME",
    ["0x50"]="ENV_LOGGER_HOOK_DETECTED",
}
local function __is_executor()
    local ok, exec = pcall(function() return identifyexecutor and identifyexecutor() end)
    if ok and exec and exec ~= "Unknown" then return true end
    if type(getgenv) == "function" or type(getgenv) == "table" then return true end
    if type(getfenv) == "function" then
        local ok2, env = pcall(getfenv)
        if ok2 and env and (env.script or env.loadstring) then return true end
    end
    if type(syn) == "table" or type(fluxus) == "table" or type(secure_call) == "function" then return true end
    return false
end
local function __at_isHooked(fn)
    if type(fn) ~= "function" then return false end
    if type(isfunctionhooked) ~= "function" then return false end
    local ok, v = pcall(isfunctionhooked, fn)
    return ok and v == true
end
local function __at_checkCritical()
    if __is_executor() then return nil end 
    if type(isfunctionhooked) ~= "function" then return nil end
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
    if ok and code then return code, __R[code] or "TAMPER" end
    ok, code = pcall(__at_checkEnvLogger)
    if ok and code then return code, __R[code] or "TAMPER" end
    return nil, nil
end
__at_code, __at_text = __at_run()
if __at_code then
    local msg = "detect body go away"
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

# ── VARIABLES Y PREDICADOS OPACOS ─────────────────────────────────────────
def generate_opaque_var(var_name: str):
    val = random.randint(2, 50)
    r = random.randint(1, 100)
    op = random.choice(['bxor', 'band', 'bor'])
    if op == 'bxor':
        expr = f"bit32.bxor({r}, {r}) + {val}"
    elif op == 'band':
        expr = f"bit32.band({r}, {r}) + {val}"
    else:
        expr = f"bit32.bor({r}, {r}) - {r} + {val}"
    return f"local {var_name} = {expr} ", val

def generate_opaque_predicate() -> str:
    r = random.randint(1, 100)
    return f"(bit32.bxor({r}, {r}) == 0)"

def generateSingleJunkLine() -> str:
    r = random.random()
    pred = generate_opaque_predicate()
    v = randomName()
    if r < 0.2:
        return f"if {pred} then local {v}={random.randint(0, 998)} end "
    elif r < 0.35:
        return f"local {v}=\"{random.randint(0, 254)}\" "
    elif r < 0.5:
        return f"if not {pred} then local {randomName()}=1 end "
    elif r < 0.7:
        return f'if type(nil)=="number" and {pred} then local {v}=1 end '
    elif r < 0.85:
        return f'do local {v}={{}} {v}["_"]=1 {v}=nil end '
    else:
        return f'if type(math.pi)=="string" and {pred} then local {v}=0 end '

def applyCFF(blocks, opaque_count: int = 2) -> str:
    stateVar = randomName()
    n = len(blocks)
    states = random.sample(range(1000, 99999), n + 1)

    op_vars = []
    prefix_code = ""
    for _ in range(opaque_count):
        ov = randomName()
        ocode, oval = generate_opaque_var(ov)
        prefix_code += ocode
        op_vars.append((ov, oval))

    cond_str = " and ".join(f"{ov}=={oval}" for ov, oval in op_vars) if op_vars else "true"
    lua = f"{prefix_code}local {stateVar}={states[0]} while true do "
    for i, block in enumerate(blocks):
        kw = "if" if i == 0 else "elseif"
        if i == 0:
            lua += f"{kw} {stateVar}=={states[i]} and ({cond_str}) then {block} {stateVar}={states[i+1]} "
        else:
            lua += f"{kw} {stateVar}=={states[i]} then {block} {stateVar}={states[i+1]} "
    lua += f"elseif {stateVar}=={states[n]} then break end end "
    return lua

# ── CODIFICACIÓN COMPACTA EN BYTES CON XOR ────────────────────────────────
def encode_bytes_xor(text: str, key: int):
    raw = text.encode("utf-8")
    out = []
    k = key & 0xFF
    for idx, b in enumerate(raw):
        out.append(b ^ ((k + idx * 11) & 0xFF))
        k = (k * 31 + b + idx) & 0xFF
    return out

def build_compact_byte_runner(text: str) -> str:
    key = random.randint(19, 237)
    enc = encode_bytes_xor(text, key)
    bytes_lua = "{" + ",".join(str(x) for x in enc) + "}"

    tbl_v, key_v, out_v, i_v, k_v, b_v, fn_v = (
        randomName(), randomName(), randomName(), randomName(),
        randomName(), randomName(), randomName()
    )
    loader_v = randomName()

    dec_code = (
        f"local {tbl_v}={bytes_lua} "
        f"local {key_v}={key} "
        f"local function {fn_v}() "
        f"local {out_v}={{}} local {k_v}=bit32.band({key_v},255) "
        f"for {i_v}=1,#{tbl_v} do "
        f"local {b_v}=bit32.bxor({tbl_v}[{i_v}],bit32.band({k_v}+({i_v}-1)*11,255)) "
        f"{out_v}[{i_v}]=string.char({b_v}) "
        f"{k_v}=bit32.band({k_v}*31+{b_v}+({i_v}-1),255) "
        f"end "
        f"return table.concat({out_v}) end "
        f"local _g=(getgenv and type(getgenv)=='function') and getgenv() or {{}} "
        f"local {loader_v}=loadstring or _g.loadstring or (getfenv and getfenv().loadstring) "
        f"if type({loader_v})=='function' then "
        f"local _ok,_chunk=pcall({loader_v},{fn_v}(),'MoonslotAT') "
        f"if _ok and type(_chunk)=='function' then pcall(_chunk) end "
        f"end "
    )
    return dec_code

def runtimeString(s: str) -> str:
    return '"' + "".join(f"\\{ord(c):03d}" for c in s.encode("utf-8")) + '"'

# ── VM COMPACTA CON FRAGMENTOS ESCAPADOS Y ORDEN ALEATORIO ───────────────
def buildTrueVM(payloadStr: str) -> str:
    STACK, POOL, ORDER = randomName(), randomName(), randomName()
    vmCore = f"local {POOL}={{}} "

    chunkSize = 36
    realChunks = [payloadStr[i:i + chunkSize] for i in range(0, len(payloadStr), chunkSize)]
    realOrder = []
    totalChunks = int(len(realChunks) * 1.2) if len(realChunks) > 1 else 1
    if totalChunks < len(realChunks):
        totalChunks = len(realChunks)
    currentReal = 0

    for i in range(1, totalChunks + 1):
        if currentReal < len(realChunks) and (
            random.random() > 0.4 or (totalChunks - i) == (len(realChunks) - currentReal)
        ):
            realOrder.append(i)
            chunk = realChunks[currentReal]
            vmCore += f"{POOL}[{i}]={runtimeString(chunk)} "
            currentReal += 1
        else:
            fake_str = "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(random.randint(5, 14)))
            vmCore += f"{POOL}[{i}]={runtimeString(fake_str)} "

    vmCore += f"local {ORDER}={{{','.join(str(n) for n in realOrder)}}} "
    idxVar = randomName()

    vmCore += f"local {STACK}={{}} for _, {idxVar} in ipairs({ORDER}) do table.insert({STACK}, {POOL}[{idxVar}]) end "
    vmCore += f"local _e = table.concat({STACK}) "
    vmCore += "local _g = (getgenv and type(getgenv)=='function') and getgenv() or {} "
    vmCore += "local _ls = loadstring or _g.loadstring or (getfenv and getfenv().loadstring) "
    vmCore += "local _as = assert or _g.assert or (getfenv and getfenv().assert) "
    vmCore += "if type(_ls) ~= 'function' then _ls = function(s) return function() end end end "
    vmCore += "local _ok, _res = pcall(_as, _ls(_e, \"=\")) "
    vmCore += "if not _ok then warn('Moonslot VM Error: '..tostring(_res)) else _res() end "
    return vmCore

def buildSingleVM(innerCode: str, handlerCount: int, opaque_count: int = 2) -> str:
    DISPATCH = randomName()
    out = f"local {DISPATCH}={{}} "
    realIdx = random.randint(0, handlerCount - 1)
    for i in range(handlerCount):
        if i == realIdx:
            out += f"{DISPATCH}[{i+1}]=function(lM) {generateSingleJunkLine()}{generateSingleJunkLine()} {innerCode} end "
        else:
            out += f"{DISPATCH}[{i+1}]=function(lM) {generateSingleJunkLine()} return nil end "
    execBlocks = [f"{DISPATCH}[{i+1}]({{}})" for i in range(handlerCount)]
    out += applyCFF(execBlocks, opaque_count=opaque_count)
    return out

# ── CAPAS CONFIGURABLES ──────────────────────────────────────────────────
def buildLayeredVM(payloadStr: str, layers: int, opaque_count: int = 2) -> str:
    vm = buildTrueVM(payloadStr)
    for _ in range(max(0, layers)):
        vm = buildSingleVM(vm, random.randint(3, 4), opaque_count=opaque_count)
    return vm

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

def obfuscate(
    sourceCode: str,
    seed: int = 0,
    vm_layers: int = 30,
    anti_tamper_layers: int = 30,
    opaque_vars: int = 2,
) -> str:
    if not sourceCode:
        return '--ERROR'
    random.seed(seed)

    antiDebug = "local _t=tick() for _=1,150000 do end if tick()-_t>5.0 then while true do task.wait(0.1) end end "
    extraProts = getExtraProtections()
    raw_at_script = (
        "local __run_at = function()\n"
        + ANTI_TAMPER_CORE.strip() + "\n"
        + "end\n"
        + "pcall(__run_at)\n"
        + antiDebug + "\n"
        + extraProts
    )

    # Anti-tamper compacto codificado en bytes + envuelto en capas
    compact_at_loader = build_compact_byte_runner(raw_at_script)
    final_protection = buildLayeredVM(compact_at_loader, anti_tamper_layers, opaque_count=opaque_vars)

    isLoadstringRegex = re.compile(
        r'loadstring\s*\(\s*game\s*:\s*HttpGet\s*\(\s*["\']([^"\']+)["\']\s*\)\s*\)\s*\(\s*\)',
        re.IGNORECASE
    )
    match = isLoadstringRegex.search(sourceCode)
    if match:
        url = match.group(1)
        payloadToProtect = f'loadstring(game:HttpGet("{url}"))()'
    else:
        payloadToProtect = sourceCode

    final_user_script = buildLayeredVM(payloadToProtect, vm_layers, opaque_count=opaque_vars)

    final_code = (
        f"{HEADER}\n\n"
        f"{final_protection}\n"
        f"{final_user_script}"
    )
    return format_lua_output(final_code, max_line=120)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--output', default='obfuscated.lua')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--vm-layers', type=int, default=30)
    ap.add_argument('--anti-tamper-layers', type=int, default=30)
    ap.add_argument('--opaque-vars', type=int, default=2)
    ap.add_argument('--min-size', type=int, default=23000)
    args = ap.parse_args()
    with open(args.input, encoding='utf-8') as f:
        src = f.read()
    out = obfuscate(
        src,
        seed=args.seed,
        vm_layers=args.vm_layers,
        anti_tamper_layers=args.anti_tamper_layers,
        opaque_vars=args.opaque_vars,
    )
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(out)

if __name__ == '__main__':
    main()
