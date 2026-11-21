import re
import random
import argparse

HEADER = '''--[[ Protected by Moonslot - Extreme Obfuscation ]]'''

# ANTI-TAMPER CORE (Intacto, sin recortes)
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

# Minificador para evitar que Arceus X se quede sin memoria y tire el error <eof>
def minify_lua(code):
    code = re.sub(r'\s+', ' ', code)
    code = re.sub(r'\s*([\+\-\*\/\=\<\>\(\)\{\}\;\,])\s*', r'\1', code)
    code = code.replace('local', ' local ').replace('function', ' function ').replace('return', ' return ')
    code = code.replace('then', ' then ').replace('do', ' do ').replace('end', ' end ')
    code = code.replace('if', ' if ').replace('elseif', ' elseif ').replace('else', ' else ')
    code = re.sub(r' +', ' ', code)
    return code.strip()

_BASE36 = "abcdefghijklmnopqrstuvwxyz"

def randomName() -> str:
    return "_" + "".join(random.choice(_BASE36) for _ in range(2)) + str(random.randint(0, 99))

# NUEVA BASURA: Matemáticas con bits (Bitwise Junk)
def generate_bitwise_junk() -> str:
    v1, v2, v3 = randomName(), randomName(), randomName()
    n1, n2 = random.randint(1000, 99999), random.randint(1000, 99999)
    n3 = random.randint(1, 8)
    
    patterns = [
        f"local {v1}=bit32.bxor({n1},{n2}) local {v2}=bit32.lshift({v1},{n3}) if not {v2} then {v1}=nil end ",
        f"local {v1}=bit32.band({n1},{n2}) local {v2}=bit32.rshift({v1},{n3}) {v3}={v1}+{v2} ",
        f"local {v1}=bit32.bor({n1},{n2}) local {v2}=bit32.bxor({v1},{n3}) if {v2}>0 then local _={v2} end ",
        f"local {v1}=bit32.extract({n1},1,4) local {v2}=bit32.replace({v1},{n2},1,4) {v1}={v2} "
    ]
    return random.choice(patterns)

def generateSingleJunkLine() -> str:
    if random.random() < 0.6:
        return generate_bitwise_junk()
    return f"local {randomName()}=1;"

def applyCFF(blocks) -> str:
    stateVar = randomName()
    n = len(blocks)
    states = random.sample(range(100, 999), n + 1)
    lua = f"local {stateVar}={states[0]} while true do "
    for i, block in enumerate(blocks):
        prefix = "if" if i == 0 else "elseif"
        lua += f"{prefix} {stateVar}=={states[i]} then {block} {stateVar}={states[i+1]} "
    lua += f"elseif {stateVar}=={states[n]} then break end end "
    return lua

def buildTrueVM(payloadStr: str) -> str:
    STACK, KEY, ORDER, POOL, B_TABLE = randomName(), randomName(), randomName(), randomName(), randomName()
    seed = random.randint(50, 249)
    vmCore = f"local {B_TABLE}={{}} for i=0,255 do {B_TABLE}[i]=string.char(i) end "
    vmCore += f"local {POOL}={{}} local {STACK}={{}} local {KEY}={seed} "
    chunkSize = 35
    realChunks = [payloadStr[i:i + chunkSize] for i in range(0, len(payloadStr), chunkSize)]
    realOrder = []
    totalChunks = int(len(realChunks) * 1.2) if len(realChunks) > 1 else 1
    if totalChunks < len(realChunks): totalChunks = len(realChunks)
    currentReal, globalIndex = 0, 0
    
    for i in range(1, totalChunks + 1):
        if currentReal < len(realChunks) and (random.random() > 0.4 or (totalChunks - i) == (len(realChunks) - currentReal)):
            realOrder.append(i)
            chunk = realChunks[currentReal]
            # Se usa \ddd para mantener el tamaño del archivo pequeño y evitar el <eof> de Arceus
            enc_str = "".join(f"\\{int(ord(chunk[j]) ^ ((seed + globalIndex + j) & 0xFF)):03d}" for j in range(len(chunk)))
            vmCore += f"{POOL}[{i}]=\"{enc_str}\" "
            globalIndex += len(chunk)
            currentReal += 1
        else:
            fake_str = "".join(f"\\{random.randint(0, 254):03d}" for _ in range(random.randint(3, 8)))
            vmCore += f"{POOL}[{i}]=\"{fake_str}\" "
            
    vmCore += f"local {ORDER}={{{','.join(str(n) for n in realOrder)}}} "
    idxVar = randomName()
    vmCore += f"local _g=0 for _,{idxVar} in ipairs({ORDER}) do local p={POOL}[{idxVar}] "
    # Desencriptación usando bits (bit32)
    vmCore += f"for j=1,#p do table.insert({STACK},string.char(bit32.bxor(string.byte(p,j),({KEY}+_g)%256)))_g=_g+1 end end "
    vmCore += f"local e=table.concat({STACK}) {STACK}=nil "
    vmCore += "local v=(getgenv and type(getgenv)=='function') and getgenv() or {} "
    vmCore += "local ls=loadstring or load or v.loadstring "
    vmCore += "if type(ls)=='function' then local ok,r=pcall(ls,e,\"=\") if ok then pcall(r) end end "
    return vmCore

def buildSingleVM(innerCode: str, handlerCount: int) -> str:
    tbl = randomName()
    out = f"local {tbl}={{}} "
    realIdx = random.randint(1, handlerCount)
    for i in range(1, handlerCount + 1):
        if i == realIdx:
            out += f"{tbl}[{i}]=function() {generate_bitwise_junk()} {innerCode} end "
        else:
            out += f"{tbl}[{i}]=function() {generate_bitwise_junk()} end "
    
    stateVar = randomName()
    states = random.sample(range(100, 999), handlerCount + 1)
    out += f"local {stateVar}={states[0]} while true do "
    for i in range(1, handlerCount + 1):
        prefix = "if" if i == 1 else "elseif"
        out += f"{prefix} {stateVar}=={states[i-1]} then pcall({tbl}[{i}]) {stateVar}={states[i]} "
    out += f"elseif {stateVar}=={states[handlerCount]} then break end end "
    return out

# 2 CAPAS DE VM SOLO PARA EL ANTI-TAMPER Y ENV LOGGER
def build2xVM(payloadStr: str) -> str:
    vm = buildTrueVM(payloadStr)
    for _ in range(2):
        vm = buildSingleVM(vm, random.randint(3, 4))
    return vm

# 18 CAPAS DE VM PARA EL SCRIPT DEL USUARIO
def build18xVM(payloadStr: str) -> str:
    vm = buildTrueVM(payloadStr)
    for _ in range(18):
        vm = buildSingleVM(vm, random.randint(2, 3))
    return vm

def buildStackObfuscation(code: str) -> str:
    nested = code
    for _ in range(random.randint(2, 3)):
        nested = f"(function() pcall(function() {nested} end) end)()"
    return nested

def split_string(s, num_parts=100):
    n = len(s)
    if n < num_parts:
        s = s + " " * (num_parts - n)
        n = len(s)
    base_len = n // num_parts
    remainder = n % num_parts
    parts = []
    start = 0
    for i in range(num_parts):
        length = base_len + (1 if i < remainder else 0)
        parts.append(s[start:start+length])
        start += length
    return parts

# LA NUEVA CUSTOM VM: Reemplaza el texto octal por instrucciones numéricas
def build_fragmented_payload(code_str, num_parts=100):
    parts = split_string(code_str, num_parts)
    
    instructions = []
    for p in parts:
        var_name = randomName() # Variable personalizada inyectada en la VM
        key = random.randint(1, 255)
        # Encriptación XOR pura
        enc_bytes = [ord(c) ^ key for c in p]
        instructions.append(f"{{'{var_name}',{{{','.join(map(str, enc_bytes))}}},{key}}}")
        
    instr_table = "{" + ",".join(instructions) + "}"
    
    # ESTA ES LA CUSTOM VM: Usa bits y variables personalizadas
    vm_script = f"""
    local I={instr_table}
    local V={{}} 
    local B={{}}
    for i=1,#I do
        local n=I[i][1]
        local d=I[i][2]
        local k=I[i][3]
        local s=""
        for j=1,#d do
            local b=bit32.bxor(d[j],k)
            s=s..string.char(b)
        end
        V[n]=s
        table.insert(B,s)
    end
    local r=table.concat(B)
    B=nil
    local l=loadstring or load
    if l then local ok,fn=pcall(l,r) if ok then pcall(fn) end end
    """
    
    # AQUI APLICAMOS LAS 2 CAPAS DE VM AL ANTI-TAMPER
    vm_reassembly = build2xVM(vm_script)
    return vm_reassembly

def obfuscate(sourceCode: str, seed: int = 0) -> str:
    if not sourceCode: return '--ERROR'
    random.seed(seed)
    
    antiDebug = "local _t=tick() for _=1,50000 do end if tick()-_t>5.0 then while true do task.wait(0.1) end end "
    protection_payload = antiDebug + "\n" + ANTI_TAMPER_CORE
    
    # Anti-Tamper fragmentado usando la Custom VM (2 capas)
    anti_tamper_final = build_fragmented_payload(protection_payload, 100)
    
    isLoadstringRegex = re.compile(r'loadstring\s*\(\s*game\s*:\s*HttpGet\s*\(\s*["\']([^"\']+)["\']\s*\)\s*\)\s*\(\s*\)', re.IGNORECASE)
    match = isLoadstringRegex.search(sourceCode)
    payloadToProtect = match.group(1) if match else sourceCode

    # Script del usuario (18 capas)
    final_user_script = build18xVM(payloadToProtect)
    final_user_script = buildStackObfuscation(final_user_script)
    
    final_code = (
        f"{HEADER}\n"
        f"local _m={{}} for i=1,50 do _m[i]=i end _m=nil pcall(collectgarbage)\n"
        f"{anti_tamper_final}\n"
        f"{final_user_script}"
    )
    
    return minify_lua(final_code)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--output', default='obfuscated.lua')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--min-size', type=int, default=23000)
    
    # parse_known_args evita que el bot de Discord arroje error con comandos extra
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
