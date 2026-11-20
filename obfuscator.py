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

def format_lua_output(code):
    return code

def randomName() -> str:
    chars = "Il1O0o_"
    return "_" + "".join(random.choice(chars) for _ in range(random.randint(4, 8)))

def randomAsciiString(length=15):
    chars = "!@#$%^&*()_+-=[]{}|;:',.<>?/`~€£¥©®°±×÷µ§"
    s = "".join(random.choice(chars) for _ in range(length))
    return s.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")

def generateSingleJunkLine() -> str:
    r = random.random()
    if r < 0.2: return f"local {randomName()}={random.randint(0, 998)} "
    elif r < 0.4: return f'local {randomName()}="{randomAsciiString()}" '
    elif r < 0.6: return f"if not(1==1) then local x=1 end "
    elif r < 0.8: 
        v = randomName()
        return f'do local {v}={{}} {v}["_"]=1 {v}=nil end '
    else: return f'if type("{randomAsciiString()}")=="string" then while true do end end '

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

# --- NUEVA FUNCIÓN: CONVIERTE BYTES A SÍMBOLOS LITERALES ---
def encode_to_lua_string(data_bytes):
    s = '"'
    for b in data_bytes:
        if b == 34: # Comilla doble
            s += '\\"'
        elif b == 92: # Barra invertida
            s += '\\\\'
        elif b == 10: # Salto de línea
            s += '\\n'
        elif b == 13: # Retorno de carro
            s += '\\r'
        elif 32 <= b <= 126:
            # Si es un carácter imprimible (letras, números, símbolos), lo ponemos literal
            s += chr(b)
        else:
            # Si es un carácter de control (invisible), lo pasamos a formato \xxx para no romper el archivo
            s += f'\\{b:03d}'
    s += '"'
    return s

def buildTrueVM(payloadStr: str) -> str:
    STACK, KEY, ORDER, POOL, B_TABLE = randomName(), randomName(), randomName(), randomName(), randomName()
    seed = random.randint(50, 249)
    
    payload_bytes = [ord(c) for c in payloadStr]
    encrypted_bytes = [b ^ ((seed + i) & 0xFF) for i, b in enumerate(payload_bytes)]
    
    chunkSize = 30
    realChunks = [encrypted_bytes[i:i + chunkSize] for i in range(0, len(encrypted_bytes), chunkSize)]
    realOrder = []
    totalChunks = int(len(realChunks) * 1.2) if len(realChunks) > 1 else 1
    if totalChunks < len(realChunks): totalChunks = len(realChunks)
    
    vmCore = f"local {POOL}={{}} "
    currentReal, globalIndex = 0, 0
    
    for i in range(1, totalChunks + 1):
        if currentReal < len(realChunks) and (random.random() > 0.4 or (totalChunks - i) == (len(realChunks) - currentReal)):
            realOrder.append(i)
            chunk = realChunks[currentReal]
            vmCore += f"{POOL}[{i}]={encode_to_lua_string(chunk)} "
            currentReal += 1
        else:
            fakeBytes = [random.randint(32, 126) for _ in range(random.randint(5, 15))] # Solo símbolos imprimibles para el relleno
            vmCore += f"{POOL}[{i}]={encode_to_lua_string(fakeBytes)} "
            
    vmCore += f"local {ORDER}={{{','.join(str(n) for n in realOrder)}}} "
    idxVar, charVar, byteVar = randomName(), randomName(), randomName()
    
    vmCore += f"for _, {idxVar} in ipairs({ORDER}) do local _s = {POOL}[{idxVar}] for {charVar}=1,#_s do "
    vmCore += f"local {byteVar} = string.byte(_s, {charVar}) "
    vmCore += f"local b = math.floor(bit32.bxor({byteVar}, ({KEY} + _gIdx) % 256)) % 256 "
    vmCore += f"table.insert({STACK}, string.char(b)) _gIdx=_gIdx+1 end end "
    
    vmCore += f"local _e = table.concat({STACK}) {STACK}=nil "
    vmCore += "local _g = (getgenv and type(getgenv)=='function') and getgenv() or {} "
    vmCore += "local _ls = loadstring or _g.loadstring or (getfenv and getfenv().loadstring) "
    vmCore += "local _as = assert or _g.assert or (getfenv and getfenv().assert) "
    vmCore += "if type(_ls) ~= 'function' then _ls = function(s) return function() end end end "
    vmCore += "local _ok, _res = pcall(_as, _ls(_e, \"=\")) "
    vmCore += "if not _ok then warn('Moonslot VM Error: '..tostring(_res)) else _res() end "
    
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

def obfuscate(sourceCode: str, seed: int = 0) -> str:
    if not sourceCode:
        return '--ERROR'
    random.seed(seed)
    
    antiDebug = "local _t=tick() for _=1,150000 do end if tick()-_t>5.0 then while true do task.wait(0.1) end end "
    extraProts = getExtraProtections()
    protection_payload = (
        "local __run_at = function()\n"
        + ANTI_TAMPER_CORE.strip() + "\n"
        + "end\n"
        + "pcall(__run_at)\n"
        + antiDebug + "\n"
        + extraProts
    )
    final_protection = build1xVM(protection_payload)
    
    isLoadstringRegex = re.compile(
        r'loadstring\s*\(\s*game\s*:\s*HttpGet\s*\(\s*["\']([^"\']+)["\']\s*\)\s*\)\s*\(\s*\)',
        re.IGNORECASE)
    match = isLoadstringRegex.search(sourceCode)
    payloadToProtect = match.group(1) if match else sourceCode
    
    final_user_script = build18xVM(payloadToProtect)
    
    fake_entries = []
    for _ in range(120): 
        length = random.randint(5, 25)
        s = "".join(random.choice("!@#$%^&*()_+-=[]{}|;:',.<>?/`~€£¥©®°±×÷µ§") for _ in range(length))
        s = s.replace('\\', '\\\\').replace('"', '\\"')
        fake_entries.append(f'"{s}"')
    
    fake_table_str = f"local Q={"{" + ",".join(fake_entries) + "} "}"
    
    final_code = (
        f"{HEADER}\n"
        f"return(function(...)\n"
        f"{fake_table_str}\n"
        f"{final_protection}\n"
        f"{final_user_script}\n"
        f"return ...\n"
        f"end)(getfenv and getfenv() or _ENV, getmetatable, unpack or table.unpack, {{...}}, select, newproxy, setmetatable)"
    )
    
    return format_lua_output(final_code)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--output', default='obfuscated.lua')
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()
    with open(args.input, encoding='utf-8') as f:
        src = f.read()
    out = obfuscate(src, seed=args.seed)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(out)

if __name__ == '__main__':
    main()
