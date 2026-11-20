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

def format_lua_output(code, max_line=1000):
    code = re.sub(r'[ \t]+', ' ', code)
    code = re.sub(r'\n+', '\n', code)
    out, buf, line_len = [], [], 0
    for line in code.split('\n'):
        line = line.strip()
        if not line: continue
        if line_len + len(line) > max_line:
            out.append(' '.join(buf))
            buf = [line]
            line_len = len(line)
        else:
            buf.append(line)
            line_len += len(line) + 1
    if buf: out.append(' '.join(buf))
    return '\n'.join(out)

_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"

def randomName() -> str:
    return "_" + "".join(random.choice(_BASE36) for _ in range(4)) + str(random.randint(0, 99))

def escape_lua_string(s: str) -> str:
    s = s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
    return f'"{s}"'

# --- TÉCNICAS DE OFUSCACIÓN ---

def layer_math_obfuscation(code, percentage=0.15):
    strings = []
    def save_string(m):
        strings.append(m.group(0))
        return f"__STR_{len(strings)-1}__"
    
    code_no_str = re.sub(r'"[^"]*"|\'[^\']*\'|\[\[.*?\]\]', save_string, code)
    numbers = list(re.finditer(r'(?<![\w.])(\d+)(?![\w.])', code_no_str))
    
    if not numbers:
        return code
        
    num_to_replace = max(1, int(len(numbers) * percentage))
    to_replace = random.sample(numbers, num_to_replace)
    to_replace.sort(key=lambda m: m.start(), reverse=True)
    
    code_list = list(code_no_str)
    for m in to_replace:
        num = int(m.group(0))
        style = random.choice([1, 2, 3])
        
        if style == 1:
            eq = f"({num} + 0)"
        elif style == 2:
            eq = f"({num} - 0)"
        else:
            if num > 1:
                a = random.randint(1, num - 1)
                eq = f"({a} + {num - a})"
            else:
                eq = f"({num} * 1)"
                
        code_list[m.start():m.end()] = list(eq)
        
    code_obf = "".join(code_list)
    
    for i, s in enumerate(strings):
        code_obf = code_obf.replace(f"__STR_{i}__", s)
        
    return code_obf

def layer_string_fragmentation(code):
    chunk_size = 80
    chunks = [code[i:i+chunk_size] for i in range(0, len(code), chunk_size)]
    frags = [escape_lua_string(c) for c in chunks]
    return f"local _s={ '..'.join(frags) } "

def layer_stack_obfuscation(code):
    v1, v2 = randomName(), randomName()
    return f"local function {v1}(f) local o,e=pcall(f) if not o then return nil end return true end local {v2}=function() {code} end {v1}({v2}) "

def layer_metamethod_hiding(code):
    tbl, mt = randomName(), randomName()
    return f"local {mt}={{__call=function(s,...) local f=function() {code} end f() end}} local {tbl}=setmetatable({{}},{mt}) {tbl}() "

def layer_memory_confusion(code):
    garbage = randomName()
    return f"local {garbage}={{}} for i=1,500 do {garbage}[i]=string.rep('A',i) end {garbage}=nil collectgarbage() {code} "

def layer_antidebugging(code):
    v1 = randomName()
    return f"local {v1}=tick() for _=1,3000 do end if tick()-{v1}>0.5 then while true do end end {code} "

def layer_dynamic_generation(code):
    s = randomName()
    return f"local {s}=function() {code} end local _ls=loadstring or getgenv().loadstring _ls('return ('..tostring({s})..')')()() "

def buildBytecodeEmulation(payloadStr: str) -> str:
    POOL, KEY, ORDER, STACK = randomName(), randomName(), randomName(), randomName()
    seed = random.randint(50, 249)
    chunkSize = 40
    realChunks = [payloadStr[i:i + chunkSize] for i in range(0, len(payloadStr), chunkSize)]
    realOrder = []
    totalChunks = int(len(realChunks) * 1.2) if len(realChunks) > 1 else 1
    if totalChunks < len(realChunks): totalChunks = len(realChunks)
    currentReal, globalIndex = 0, 0

    vmCore = f"local {POOL}={{}} "
    for i in range(1, totalChunks + 1):
        if currentReal < len(realChunks) and (random.random() > 0.4 or (totalChunks - i) == (len(realChunks) - currentReal)):
            realOrder.append(i)
            chunk = realChunks[currentReal]
            hexBytes = []
            for j in range(len(chunk)):
                b = ord(chunk[j]) ^ ((seed + globalIndex) & 0xFF)
                hexBytes.append(f"{b:02x}")
                globalIndex += 1
            vmCore += f'{POOL}[{i}]="{("".join(hexBytes))}" '
            currentReal += 1
        else:
            fakeHex = ''.join(f"{random.randint(0,255):02x}" for _ in range(random.randint(10, 30)))
            vmCore += f'{POOL}[{i}]="{fakeHex}" '

    gi, oi, cv, dv = randomName(), randomName(), randomName(), randomName()
    vmCore += f"local {ORDER}={{{','.join(str(n) for n in realOrder)}}} "
    vmCore += f"local {STACK}={{}} local {gi}=0 "
    vmCore += f"for _,{oi} in ipairs({ORDER}) do "
    vmCore += f"local {cv}={POOL}[{oi}] "
    vmCore += f"local {dv}={cv}:gsub('%x%x',function(h) local b=bit32.bxor(tonumber(h,16),(({KEY}+{gi})%256)) {gi}={gi}+1 return string.char(b) end) "
    vmCore += f"table.insert({STACK},{dv}) end "
    vmCore += f"local _e=table.concat({STACK}) {STACK}=nil "
    vmCore += "local _g=(getgenv and type(getgenv)=='function') and getgenv() or {} "
    vmCore += "local _ls=loadstring or _g.loadstring or (getfenv and getfenv().loadstring) "
    vmCore += "local _ok,_res=pcall(_ls,_e,\"=\") "
    vmCore += "if _ok then _res() end "
    return vmCore

def layer_function_splitting_and_deadcode(code, iterations=1):
    vm = code
    for _ in range(iterations):
        DISPATCH = randomName()
        handlerCount = random.randint(3, 4)
        realIdx = random.randint(0, handlerCount - 1)
        out = f"local {DISPATCH}={{}} "
        
        for i in range(handlerCount):
            if i == realIdx:
                out += f"{DISPATCH}[{i+1}]=function(lM) if(math.random()>2)then local _z=1 while _z==1 do end end {vm} end "
            else:
                out += f"{DISPATCH}[{i+1}]=function(lM) if type(nil)=='table' then local q={{}} q[1]=1 end return nil end "
                
        stateVar = randomName()
        states = random.sample(range(1000, 99999), handlerCount + 1)
        out += f"local {stateVar}={states[0]} while true do "
        for i in range(handlerCount):
            prefix = "if" if i == 0 else "elseif"
            out += f"{prefix} {stateVar}=={states[i]} then {DISPATCH}[{i+1}]({{}}) {stateVar}={states[i+1]} "
        out += f"elseif {stateVar}=={states[handlerCount]} then break end end "
        
        vm = out
    return vm

def apply_all_layers(payload_str, iterations=1, math_percent=0.15):
    payload = buildBytecodeEmulation(payload_str)
    
    for _ in range(iterations):
        payload = layer_string_fragmentation(payload)
        payload = layer_function_splitting_and_deadcode(payload, iterations=1)
        payload = layer_math_obfuscation(payload, percentage=math_percent)
        payload = layer_stack_obfuscation(payload)
        payload = layer_metamethod_hiding(payload)
        payload = layer_antidebugging(payload)
        payload = layer_dynamic_generation(payload)
        payload = layer_memory_confusion(payload)
        
    return payload

def getExtraProtections() -> str:
    return "pcall(function() if math.pi<3.14 or math.pi>3.15 then error('math') end end) "

def obfuscate(sourceCode: str, seed: int = 0) -> str:
    if not sourceCode: return '--ERROR'
    random.seed(seed)
    
    protection_payload = "local __run=function() " + ANTI_TAMPER_CORE.strip() + " end pcall(__run) " + getExtraProtections()
    final_protection = apply_all_layers(protection_payload, iterations=2, math_percent=0.10)
    
    isLoadstringRegex = re.compile(r'loadstring\s*\(\s*game\s*:\s*HttpGet\s*\(\s*["\']([^"\']+)["\']\s*\)\s*\)\s*\(\s*\)', re.IGNORECASE)
    match = isLoadstringRegex.search(sourceCode)
    payloadToProtect = match.group(1) if match else sourceCode
    
    final_user_script = apply_all_layers(payloadToProtect, iterations=1, math_percent=0.15)
    
    final_code = f"{HEADER}\n{final_protection}\n{final_user_script}"
    return format_lua_output(final_code, max_line=1000)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--output', default='obfuscated.lua')
    ap.add_argument('--seed', type=int, default=0)
    # Agregamos de nuevo --min-size para que tu bot no de error
    ap.add_argument('--min-size', type=int, default=23000) 
    args = ap.parse_args()
    
    with open(args.input, encoding='utf-8') as f:
        src = f.read()
    out = obfuscate(src, seed=args.seed)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(out)

if __name__ == '__main__':
    main()
