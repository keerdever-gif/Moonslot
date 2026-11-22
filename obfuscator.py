import re
import random
import argparse
import base64

HEADER = '''--[[
  Protected by Moonslot - Extreme Obfuscation
  Unauthorized reproduction or distribution is prohibited.
]]\n'''

ANCHOR_SYMBOLS = list("@#€_&-+()/*\"':;!?")

def generate_pool_tag() -> str:
    suffix = "".join(random.choice(ANCHOR_SYMBOLS) for _ in range(5))
    return f"[pool.a.d.d._{suffix}]"

def lua_quote(s: str) -> str:
    escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
    return f'"{escaped}"'

ANTI_TAMPER_CORE = r'''
local _s = function(...) return table.concat({...}) end
local _tampered = false
local _pool_list = __POOL_LIST_PLACEHOLDER__
local _hooked = _G[_s("is", "function", "hooked")]

local function _check_pools()
    local root = (getgenv and type(getgenv) == "function") and getgenv() or _G
    if type(root) ~= "table" or type(_pool_list) ~= "table" or #_pool_list == 0 then
        _tampered = true
        return
    end
    for _, key in ipairs(_pool_list) do
        if root[key] == nil then
            _tampered = true
            return
        end
    end
end

local function _check_hooks()
    if type(_hooked) == "function" then
        local fns = {pcall, type, tostring, next, pairs, rawget, rawset, setmetatable, getfenv, setfenv}
        for _, fn in ipairs(fns) do
            local ok, res = pcall(_hooked, fn)
            if ok and res == true then _tampered = true end
        end
    end
    local env = (getgenv and type(getgenv) == "function") and getgenv() or _G
    for k, v in pairs(env) do
        local ks = tostring(k)
        if type(v) == "function" and (string.find(ks, "hook") or string.find(ks, "detour") or string.find(ks, "clone")) then
            _tampered = true
        end
    end
end

local function _check_debug()
    if type(debug) == "table" and type(debug.gethook) == "function" then
        local ok, hook = pcall(debug.gethook)
        if ok and hook ~= nil then _tampered = true end
    end
end

pcall(_check_pools)
pcall(_check_hooks)
pcall(_check_debug)
'''

_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"

def randomName() -> str:
    return "_" + "".join(random.choice(_BASE36) for _ in range(6)) + str(random.randint(0, 999))

def generate_opaque_predicate() -> str:
    r = random.randint(1, 100)
    return f"(bit32.bxor({r}, {r}) == 0)"

def generateSingleJunkLine(pool_tags=None) -> str:
    r = random.random()
    pred = generate_opaque_predicate()
    v = randomName()
    pool_snippet = ""
    if pool_tags:
        tag = random.choice(pool_tags)
        pool_snippet = (
            f"local _rt=(getgenv and type(getgenv)=='function') and getgenv() or _G "
            f"if type(_rt)=='table' and _rt[{lua_quote(tag)}]==nil then _tampered=true end "
        )
    if r < 0.2:
        return f"if {pred} then {pool_snippet}local {v}={random.randint(0, 998)} end "
    elif r < 0.4:
        return f"local {v}={{}} for i=1,30 do {v}[i]=string.rep('x',5) end {pool_snippet}"
    elif r < 0.6:
        return f"do local {v}=setmetatable({{}},{{__index=function() return math.random() end,__metatable='locked'}}) end {pool_snippet}"
    elif r < 0.8:
        return f"pcall(function() if {pred} then return string.len('random') end end) {pool_snippet}"
    else:
        return f"local {v}=math.floor(math.random({random.randint(1,50)},500)) {pool_snippet}"

def obfuscate_identifiers(code: str) -> str:
    keywords = {
        'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function',
        'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then', 'true',
        'until', 'while', 'pcall', 'type', 'math', 'string', 'table', 'bit32',
        'game', 'task', 'loadstring', 'getfenv', 'getgenv', 'setfenv', 'debug',
        'ipairs', 'pairs', 'next', 'tostring', 'rawget', 'rawset', 'setmetatable',
        'getmetatable', '_G', '_tampered'
    }
    local_vars = set(re.findall(r'\blocal\s+([a-zA-Z_][a-zA-Z0-9_]*)', code))
    for var in local_vars:
        if var not in keywords and len(var) > 1:
            new_var = randomName()
            code = re.sub(rf'(?<![\w\.\:])\b{re.escape(var)}\b(?![\w\:])', new_var, code)
    return code

def applyCFF(blocks) -> str:
    stateVar = randomName()
    n = len(blocks)
    states = random.sample(range(1000, 99999), n + 1)
    lua = f"local {stateVar}={states[0]} while true do "
    for i, block in enumerate(blocks):
        prefix = "if" if i == 0 else "elseif"
        lua += f"{prefix} {stateVar}=={states[i]} and {generate_opaque_predicate()} then {block} {stateVar}={states[i+1]} "
    lua += f"elseif {stateVar}=={states[n]} then break end end "
    return lua

def generate_b64_soup(pool, idx, b64, pool_tags=None):
    pieces = [b64[i:i+8] for i in range(0, len(b64), 8)]
    pieces_table = ",".join(f"'{p}'" for p in pieces)

    r = random.random()
    if r < 0.25:
        return f"{pool}[{idx}]=table.concat({{{pieces_table}}}) "
    elif r < 0.5:
        v = randomName()
        return f"do local {v}=table.concat({{{pieces_table}}}) if {generate_opaque_predicate()} then {pool}[{idx}]={v} end end "
    elif r < 0.75:
        return f"if {generate_opaque_predicate()} then {pool}[{idx}]=table.concat({{{pieces_table}}}) end "
    else:
        v1, v2 = randomName(), randomName()
        return f"local {v1}={{{pieces_table}}} local {v2}=table.concat({v1}) {pool}[{idx}]={v2} "

def buildTrueVM(payloadStr: str, pool_tags) -> str:
    STACK, KEY1, KEY2, ORDER, POOL, B_TABLE = (
        randomName(), randomName(), randomName(), randomName(), randomName(), randomName()
    )
    seed1 = random.randint(10, 250)
    seed2 = random.randint(20, 240)

    B64_TABLE = randomName()
    DECODE_FUNC = randomName()
    CORRUPT_FN = randomName()
    check_tag = lua_quote(random.choice(pool_tags))

    vmCore = f"local {B_TABLE}={{}} for i=0,255 do {B_TABLE}[i]=string.char(i) end "
    vmCore += f"local {STACK}={{}} local {KEY1}={seed1} local {KEY2}={seed2} "

    vmCore += (
        f"local function {CORRUPT_FN}() "
        f"local _rt=(getgenv and type(getgenv)=='function') and getgenv() or _G "
        f"if _tampered or type(_rt)~='table' or _rt[{check_tag}]~=true then "
        f"{KEY1}=({KEY1}+math.random(17,97))%256 {KEY2}=({KEY2}+math.random(13,89))%256 "
        f"end end {CORRUPT_FN}() "
    )

    ls_chars = ",".join(str(ord(c)) for c in "loadstring")
    vmCore += f"local _ls_name=string.char({ls_chars}) "

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
    totalChunks = int(len(realChunks) * 1.25) if len(realChunks) > 1 else 1
    if totalChunks < len(realChunks):
        totalChunks = len(realChunks)
    currentReal, globalIndex = 0, 0

    for i in range(1, totalChunks + 1):
        if currentReal < len(realChunks) and (
            random.random() > 0.3 or (totalChunks - i) == (len(realChunks) - currentReal)
        ):
            realOrder.append(i)
            chunk = realChunks[currentReal]
            chunk_bytes = chunk.encode('utf-8')
            encryptedBytes = bytearray()
            for j in range(len(chunk_bytes)):
                enc_byte = chunk_bytes[j] ^ ((seed1 + globalIndex * seed2) & 0xFF)
                encryptedBytes.append(enc_byte)
                globalIndex += 1
            b64_str = base64.b64encode(encryptedBytes).decode('ascii')
            vmCore += generate_b64_soup(POOL, i, b64_str, pool_tags)
            currentReal += 1
        else:
            fake_bytes = bytes([random.randint(0, 255) for _ in range(random.randint(5, 20))])
            b64_fake = base64.b64encode(fake_bytes).decode('ascii')
            vmCore += generate_b64_soup(POOL, i, b64_fake, pool_tags)

    vmCore += f" local {ORDER}={{{','.join(str(n) for n in realOrder)}}} "
    idxVar, jVar = randomName(), randomName()
    vmCore += f"local _gIdx=0 for _,{idxVar} in ipairs({ORDER}) do "
    vmCore += f"local dec_chunk={DECODE_FUNC}({POOL}[{idxVar}]) "
    vmCore += f"for {jVar}=1,#dec_chunk do local b=dec_chunk:byte({jVar}) "
    vmCore += f"local rot=({KEY1}+_gIdx*{KEY2})%256 "
    vmCore += f"local real_b=math.floor(bit32.bxor(b,rot))%256 "
    vmCore += f"table.insert({STACK},{B_TABLE}[real_b]) _gIdx=_gIdx+1 end end "
    vmCore += f"local _e=table.concat({STACK}) {STACK}=nil "

    vmCore += "local _g=(getgenv and type(getgenv)=='function') and getgenv() or _G "
    vmCore += "local _env=setmetatable({},{__index=_g}) "
    vmCore += "local _ls=_g[_ls_name] or (getfenv and getfenv()[_ls_name]) or loadstring "
    vmCore += "if type(_ls)=='function' then local _ok,_res=pcall(_ls,_e,'=') "
    vmCore += "if _ok and type(_res)=='function' then pcall(setfenv,_res,_env) pcall(_res) end end "
    return vmCore

def buildSingleVM(innerCode: str, handlerCount: int, pool_tags) -> str:
    style = random.choice(["metatable", "ifchain", "cff"])
    DISPATCH = randomName()
    STORE = randomName()
    MT = randomName()
    out = f"local {STORE}={{}} local {MT}={{__index=function(t,k) return {STORE}[k] end,__metatable='locked'}} local {DISPATCH}=setmetatable({{}},{MT}) "
    realIdx = random.randint(0, handlerCount - 1)
    for i in range(handlerCount):
        if i == realIdx:
            out += f"{STORE}[{i+1}]=function(lM) {generateSingleJunkLine(pool_tags)} {innerCode} end "
        else:
            out += f"{STORE}[{i+1}]=function(lM) {generateSingleJunkLine()} return nil end "

    if style == "cff":
        execBlocks = [f"{DISPATCH}[{i+1}]({{}})" for i in range(handlerCount)]
        out += applyCFF(execBlocks)
    elif style == "ifchain":
        sel = randomName()
        target = realIdx + 1
        out += f"local {sel}={target} "
        for i in range(handlerCount):
            kw = "if" if i == 0 else "elseif"
            out += f"{kw} {sel}=={i+1} and {generate_opaque_predicate()} then {DISPATCH}[{i+1}]({{}}) "
        out += "end "
    else:
        execBlocks = [f"{DISPATCH}[{i+1}]({{}})" for i in range(handlerCount)]
        out += applyCFF(execBlocks)
    return out

def buildMultiVM(payloadStr: str, pool_tags, layers: int = 5) -> str:
    vm = buildTrueVM(payloadStr, pool_tags)
    for _ in range(layers):
        vm = buildSingleVM(vm, random.randint(3, 4), pool_tags)
    return vm

def buildStackObfuscation(code: str, pool_tags) -> str:
    nested = code
    for _ in range(random.randint(2, 3)):
        tag_chk = ""
        if pool_tags:
            t = lua_quote(random.choice(pool_tags))
            tag_chk = (
                f"local _rt=(getgenv and type(getgenv)=='function') and getgenv() or _G "
                f"if type(_rt)~='table' or _rt[{t}]~=true then return end "
            )
        nested = f"(function() pcall(function() {tag_chk}{nested} end) end)(); "
    return nested

def getExtraProtections(pool_tags) -> str:
    checks = "\n".join(
        f'    if type(_rt) ~= "table" or _rt[{lua_quote(tag)}] ~= true then error("pool missing") end'
        for tag in pool_tags
    )
    return f"""
pcall(function()
    local _rt = (getgenv and type(getgenv) == "function") and getgenv() or _G
{checks}
    if math.floor(1.5) ~= 1 then error("m") end
    if string.len("a") ~= 1 then error("s") end
    local t = setmetatable({{}}, {{__metatable = "locked"}})
    if getmetatable(t) ~= "locked" then error("mt") end
end)
"""

def minify_payload(code):
    code = re.sub(r'--\[\[.*?\]\]', '', code, flags=re.DOTALL)
    code = re.sub(r'--[^\n]*', '', code)

    tokens = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if c in '"\'':
            quote = c
            j = i + 1
            while j < n and code[j] != quote:
                if code[j] == '\\':
                    j += 1
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

    pool_count = random.randint(3, 5)
    pool_tags = [generate_pool_tag() for _ in range(pool_count)]
    pool_list_lua = "{" + ",".join(lua_quote(t) for t in pool_tags) + "}"
    reg_pools = " ".join(
        f"if type(_rt)=='table' then _rt[{lua_quote(tag)}]=true end"
        for tag in pool_tags
    )

    minified_user_code = minify_payload(sourceCode)
    obfuscated_user_code = obfuscate_identifiers(minified_user_code)

    at_core = ANTI_TAMPER_CORE.replace("__POOL_LIST_PLACEHOLDER__", pool_list_lua)
    antiDebug = "local _t=tick() for _=1,150000 do end if tick()-_t>5.0 then while true do task.wait(0.1) end end "
    extraProts = getExtraProtections(pool_tags)

    final_user_script = buildMultiVM(obfuscated_user_code, pool_tags, layers=5)
    final_user_script = buildStackObfuscation(final_user_script, pool_tags)

    protection_payload = antiDebug + "\n" + extraProts + "\n" + at_core
    protection_payload = minify_payload(protection_payload)
    anti_tamper_final = buildMultiVM(protection_payload, pool_tags, layers=4)

    init_pools = (
        f"local _rt=(getgenv and type(getgenv)=='function') and getgenv() or _G "
        f"{reg_pools} "
    )

    final_code = (
        f"local _mc={{}} for i=1,1000 do _mc[i]=string.rep('X',40) end _mc=nil pcall(collectgarbage) "
        f"{init_pools}"
        f"{anti_tamper_final} "
        f"{final_user_script}"
    )

    return HEADER + minify_payload(final_code)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--output', default='obfuscated.lua')
    ap.add_argument('--seed', type=int, default=0)

    args, _ = ap.parse_known_args()

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
