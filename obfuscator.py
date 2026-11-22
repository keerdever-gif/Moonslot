import re
import random
import argparse
import base64

HEADER = '''--[[
  Protected by Moonslot - Extreme Obfuscation
  Unauthorized reproduction or distribution is prohibited.
]]\n'''

ANCHOR_SYMBOLS = list("@#€_&-+()/*:;!?")

def generate_pool_tag() -> str:
    suffix = "".join(random.choice(ANCHOR_SYMBOLS) for _ in range(5))
    return f"[pool.a.d.d._{suffix}]"

def lua_quote(s: str) -> str:
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'

BOOTSTRAP_HELPERS = (
    "local _T=type "
    "local _bx=(type(bit32)=='table'and type(bit32.bxor)=='function')and bit32.bxor or function(a,b)"
    "local r,p=0,1 while a>0 or b>0 do if(a%2)~=(b%2)then r=r+p end a=math.floor(a/2)b=math.floor(b/2)p=p*2 end return r end "
    "local _ch=(type(string)=='table'and type(string.char)=='function')and string.char or function(x)return''end "
    "local _rp=(type(string)=='table'and type(string.rep)=='function')and string.rep or function(s,n)local o=''for _=1,n do o=o..s end return o end "
    "local _tc=(type(table)=='table'and type(table.concat)=='function')and table.concat or function(t)return table.concat and table.concat(t)or''end "
    "local _ti=(type(table)=='table'and type(table.insert)=='function')and table.insert or function(t,v)t[#t+1]=v end "
    "local _fl=(type(math)=='table'and type(math.floor)=='function')and math.floor or function(x)return x-(x%1)end "
    "local _rn=(type(math)=='table'and type(math.random)=='function')and math.random or function(a,b)return a or 0 end "
    "local _er=type(error)=='function'and error or function()end "
    "local _RT=(getgenv and _T(getgenv)=='function')and getgenv()or _G "
)

ANTI_TAMPER_CORE = r'''
local _s = function(...) return table.concat({...}) end
local _tampered = false
local _pool_list = __POOL_LIST_PLACEHOLDER__
local _root = (getgenv and type(getgenv) == "function") and getgenv() or _G

local function _safe_pcall(fn, ...)
    if type(fn) ~= "function" then
        return false, nil
    end
    if type(pcall) == "function" then
        return pcall(fn, ...)
    end
    return true, fn(...)
end

local function _dtc()
    _tampered = true
    error("Moonslot detect you", 0)
end

local function _check_pools()
    if type(_root) ~= "table" or type(_pool_list) ~= "table" or #_pool_list == 0 then
        _dtc()
    end
    for _, key in ipairs(_pool_list) do
        if _root[key] == nil then
            _dtc()
        end
    end
end

local function _check_spy_and_globals()
    if type(_root) == "table" then
        if type(rawget) == "function" and rawget(_root, "Spy") ~= nil then
            _dtc()
        end
        for k, v in pairs(_root) do
            local ks = tostring(k)
            if type(v) == "function" and (string.find(ks, "hook") or string.find(ks, "detour") or string.find(ks, "logger") or string.find(ks, "spy")) then
                _dtc()
            end
        end
    end
    _safe_pcall(function()
        if (_G and _G.Spy ~= nil) or Spy ~= nil then
            _dtc()
        end
    end)
end

local function _check_print_and_debug()
    if type(tostring(print)) == "string" and tostring(print):match("^function: 0x0000") then
        _dtc()
    end
    if type(debug) == "table" and type(debug.gethook) == "function" then
        local ok, hook = _safe_pcall(debug.gethook)
        if ok and hook ~= nil then
            _dtc()
        end
    end
    _safe_pcall(function()
        if type(debug) == "table" and type(debug.getinfo) == "function" then
            local info = debug.getinfo(function() end, "u")
            if type(info) ~= "table" or info.nups == nil then
                _dtc()
            end
        end
    end)
end

local function _check_string_char_and_buffer()
    local okChar, resChar = _safe_pcall(string.char, nil)
    if okChar and resChar == "" then
        _dtc()
    end
    if type(buffer) == "table" and type(buffer.fromstring) == "function" then
        _safe_pcall(function()
            local str = "moonslot_env_check"
            local buf = buffer.fromstring(str)
            local okSvc, svc = _safe_pcall(function() return game:GetService("EncodingService") end)
            if okSvc and type(typeof) == "function" and typeof(svc) == "Instance" then
                local okComp, comp = _safe_pcall(function()
                    local e = svc:CompressBuffer(buf, Enum.CompressionAlgorithm.Zstd, 1)
                    local d = svc:DecompressBuffer(e, Enum.CompressionAlgorithm.Zstd)
                    return buffer.tostring(d) == str
                end)
                if not okComp or not comp then
                    _dtc()
                end
            end
        end)
    end
end

local function _check_server_service()
    local ok = _safe_pcall(function()
        local _ = game:GetService("ServerScriptService"):GetChildren()
    end)
    if ok then
        _dtc()
    end
end

local function _check_coroutine_and_metatables()
    if type(coroutine) == "table" and type(coroutine.create) == "function" and type(coroutine.resume) == "function" then
        local co = coroutine.create(function()
            coroutine.yield(10)
            coroutine.yield(20)
        end)
        local _, v1 = coroutine.resume(co)
        local _, v2 = coroutine.resume(co)
        if v1 ~= 10 or v2 ~= 20 then
            _dtc()
        end
    end
    local mt = setmetatable({}, {__index = function(_, k) return tostring(k) .. "_ok" end})
    if mt["env"] ~= "env_ok" then
        _dtc()
    end
    local rawT = setmetatable({}, {__newindex = function() end})
    if type(rawset) == "function" and type(rawget) == "function" then
        rawset(rawT, "val", 42)
        if rawget(rawT, "val") ~= 42 then
            _dtc()
        end
    end
    _safe_pcall(function()
        local a = game:GetService("Players")
        local b = game:GetService("Players")
        if a ~= b then
            _dtc()
        end
    end)
    _safe_pcall(function()
        local obj = Instance.new("Part")
        obj.Parent = workspace
        obj:Destroy()
        if obj.Parent ~= nil then
            _dtc()
        end
    end)
    _safe_pcall(function()
        local s = Instance.new("Sound")
        local okLoud = _safe_pcall(function() s.PlaybackLoudness = 5 end)
        if okLoud then
            s:Destroy()
            _dtc()
        end
        s:Destroy()
    end)
end

local function _check_debug_constants_and_hooks()
    _safe_pcall(function()
        if type(debug) == "table" and type(debug.getconstants) == "function" and type(debug.setconstant) == "function" then
            local function probeFn()
                local a = "cat"
                return a
            end
            local c = debug.getconstants(probeFn)
            local idx = nil
            if type(c) == "table" then
                for i, v in pairs(c) do
                    if v == "cat" then
                        idx = i
                        break
                    end
                end
            end
            if idx and idx > 0 then
                local st = _safe_pcall(debug.setconstant, probeFn, idx, "dog")
                if st and probeFn() == "dog" then
                    _dtc()
                end
            end
        end
    end)
    _safe_pcall(function()
        if type(clonefunction) == "function" and type(hookfunction) == "function" then
            local function probeA() return 1 end
            local ca = clonefunction(probeA)
            local st = _safe_pcall(hookfunction, probeA, function() return 2 end)
            if st and probeA() == 2 and ca() == 1 then
                _dtc()
            end
        end
    end)
end

local function _check_timing_and_env()
    _safe_pcall(function()
        if type(getgenv) == "function" and type(typeof) == "function" and typeof(getgenv) == "function" then
            local c = os.clock
            local w = task and task.wait
            local m = math.sin
            if type(c) == "function" and type(w) == "function" and type(m) == "function" then
                local t1 = c()
                w(0.15)
                local t2 = c()
                local f = t2 - t1
                if f >= 0.14 and f < 0.8 then
                    local a = 0
                    local t3 = c()
                    for i = 1, 100000 do
                        a = a + m(i * 0.05)
                    end
                    local t4 = c()
                    local d = t4 - t3
                    if d <= 0.0001 or (type(_root) == "table" and typeof(_root.math) ~= "table") then
                        _dtc()
                    end
                end
            end
        end
    end)
end

_safe_pcall(_check_pools)
_safe_pcall(_check_spy_and_globals)
_safe_pcall(_check_print_and_debug)
_safe_pcall(_check_string_char_and_buffer)
_safe_pcall(_check_server_service)
_safe_pcall(_check_coroutine_and_metatables)
_safe_pcall(_check_debug_constants_and_hooks)
_safe_pcall(_check_timing_and_env)
'''

_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"

def randomName() -> str:
    return "_" + random.choice("abcdefghijklmnopqrstuvwxyz") + "".join(random.choice(_BASE36) for _ in range(random.randint(1, 3))) + str(random.randint(0, 99))

def generate_opaque_predicate() -> str:
    r = random.randint(1, 99)
    return f"(_bx({r},{r})==0)"

def generateSingleJunkLine(pool_tags=None) -> str:
    pred = generate_opaque_predicate()
    v = randomName()
    pool_snippet = ""
    if pool_tags:
        tag = random.choice(pool_tags)
        pool_snippet = f"if _RT and _RT[{lua_quote(tag)}]==nil then _tampered=true _er('Moonslot detect you',0)end "
    variants = [
        f"if {pred} then {pool_snippet}local {v}={random.randint(0,998)} end ",
        f"local {v}={{}}for i=1,8 do {v}[i]=_rp('x',2)end {pool_snippet}",
        f"do local {v}=setmetatable({{}},{{__index=function()return _rn()end,__metatable='locked'}})end {pool_snippet}",
        f"if _T(pcall)=='function'then pcall(function()if {pred} then return #('random')end end)end {pool_snippet}",
        f"local {v}=_fl(_rn({random.randint(1,50)},500)){pool_snippet}",
    ]
    return random.choice(variants)

def obfuscate_identifiers(code: str) -> str:
    keywords = {
        'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function',
        'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then', 'true',
        'until', 'while', 'pcall', 'type', 'math', 'string', 'table', 'bit32',
        'game', 'task', 'loadstring', 'getfenv', 'getgenv', 'setfenv', 'debug',
        'ipairs', 'pairs', 'next', 'tostring', 'rawget', 'rawset', 'setmetatable',
        'getmetatable', 'typeof', 'coroutine', 'buffer', 'os', 'Instance', 'workspace',
        'clonefunction', 'hookfunction', 'collectgarbage', '_G', '_RT', '_tampered', 'Spy',
        '_T', '_bx', '_ch', '_rp', '_tc', '_ti', '_fl', '_rn', '_er'
    }
    local_vars = set(re.findall(r'\blocal\s+(?:function\s+)?([a-zA-Z_][a-zA-Z0-9_]*)', code))
    for var in local_vars:
        if var not in keywords and len(var) > 1:
            new_var = randomName()
            code = re.sub(rf'(?<![\w\.\:])\b{re.escape(var)}\b(?![\w\:])', new_var, code)
    return code

def applyCFF(blocks) -> str:
    stateVar = randomName()
    n = len(blocks)
    states = random.sample(range(100, 9999), n + 1)
    lua = f"local {stateVar}={states[0]} while true do "
    for i, block in enumerate(blocks):
        prefix = "if" if i == 0 else "elseif"
        lua += f"{prefix} {stateVar}=={states[i]} and {generate_opaque_predicate()} then {block} {stateVar}={states[i+1]} "
    lua += f"elseif {stateVar}=={states[n]} then break end end "
    return lua

def generate_b64_soup(pool, idx, b64, pool_tags=None):
    step = random.randint(8, 16)
    pieces_ordered = [b64[i:i+step] for i in range(0, len(b64), step)]
    pieces_table = ",".join(f"'{p}'" for p in pieces_ordered)

    tag_guard = ""
    if pool_tags and random.random() < 0.25:
        t = lua_quote(random.choice(pool_tags))
        tag_guard = f"if _RT and _RT[{t}]==nil then _er('Moonslot detect you',0)end "

    r = random.random()
    if r < 0.35:
        return f"{tag_guard}{pool}[{idx}]=_tc({{{pieces_table}}}) "
    elif r < 0.7:
        v = randomName()
        return f"do local {v}=_tc({{{pieces_table}}})if {generate_opaque_predicate()}then {pool}[{idx}]={v} end end {tag_guard}"
    else:
        v1 = randomName()
        return f"local {v1}={{{pieces_table}}} {pool}[{idx}]={v1} {tag_guard}"

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

    vmCore = f"local _tampered=false local {POOL}={{}}local {B_TABLE}={{}}for i=0,255 do {B_TABLE}[i]=_ch(i)end "
    vmCore += f"local {STACK}={{}} local {KEY1}={seed1} local {KEY2}={seed2} "

    vmCore += (
        f"local function {CORRUPT_FN}() "
        f"if _tampered or _T(_RT)~='table' or _RT[{check_tag}]~=true then "
        f"{KEY1}=({KEY1}+_fl(_rn(17,97)))%256 {KEY2}=({KEY2}+_fl(_rn(13,89)))%256 "
        f"_er('Moonslot detect you',0) "
        f"end end {CORRUPT_FN}() "
    )

    ls_chars = ",".join(str(ord(c)) for c in "loadstring")
    vmCore += f"local _ls_key=_ch({ls_chars}) "

    vmCore += f"local {B64_TABLE}='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/' "
    vmCore += f"local function {DECODE_FUNC}(data) local res={{}}local i=1 while i<=#data do "
    vmCore += f"local b1,b2,b3,b4=data:byte(i,i+3) "
    vmCore += f"local c1,c2,c3,c4={B64_TABLE}:find(_ch(b1),1,true),{B64_TABLE}:find(_ch(b2),1,true),{B64_TABLE}:find(_ch(b3),1,true),{B64_TABLE}:find(_ch(b4),1,true) "
    vmCore += f"c1,c2,c3,c4=c1-1,c2 and c2-1,c3 and c3-1,c4 and c4-1 "
    vmCore += f"local byte1=_fl(c1*4+(c2 or 0)/16) "
    vmCore += f"local byte2=_fl(((c2 or 0)%16)*16+(c3 or 0)/4) "
    vmCore += f"local byte3=_fl(((c3 or 0)%4)*64+(c4 or 0)) "
    vmCore += f"_ti(res,_ch(byte1)) "
    vmCore += f"if c3 then _ti(res,_ch(byte2))end if c4 then _ti(res,_ch(byte3))end "
    vmCore += f"i=i+4 end return _tc(res)end "

    chunkSize = 56
    realChunks = [payloadStr[i:i + chunkSize] for i in range(0, len(payloadStr), chunkSize)]
    realOrder = []
    totalChunks = max(len(realChunks), int(len(realChunks) * 1.15) if len(realChunks) > 1 else 1)
    currentReal, globalIndex = 0, 0

    soup_items = []
    for i in range(1, totalChunks + 1):
        if currentReal < len(realChunks) and (
            random.random() > 0.25 or (totalChunks - i) == (len(realChunks) - currentReal)
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
            soup_items.append(generate_b64_soup(POOL, i, b64_str, pool_tags))
            currentReal += 1
        else:
            fake_bytes = bytes([random.randint(0, 255) for _ in range(random.randint(5, 14))])
            b64_fake = base64.b64encode(fake_bytes).decode('ascii')
            soup_items.append(generate_b64_soup(POOL, i, b64_fake, pool_tags))

    random.shuffle(soup_items)
    vmCore += " " + " ".join(soup_items) + " "

    vmCore += f" local {ORDER}={{{','.join(str(n) for n in realOrder)}}} "
    idxVar, jVar = randomName(), randomName()
    vmCore += f"local _gIdx=0 for _,{idxVar} in ipairs({ORDER})do "
    vmCore += f"local dec_chunk={DECODE_FUNC}({POOL}[{idxVar}]) "
    vmCore += f"for {jVar}=1,#dec_chunk do local b=dec_chunk:byte({jVar}) "
    vmCore += f"local rot=({KEY1}+_gIdx*{KEY2})%256 "
    vmCore += f"local real_b=_fl(_bx(b,rot))%256 "
    vmCore += f"_ti({STACK},{B_TABLE}[real_b])_gIdx=_gIdx+1 end end "
    vmCore += f"local _e=_tc({STACK}){STACK}=nil "

    vmCore += "local _g=(getgenv and _T(getgenv)=='function')and getgenv()or _G "
    vmCore += "local _fenv=(getfenv and _T(getfenv)=='function' and _T(pcall)=='function' and pcall(getfenv,0))and getfenv(0)or _G "
    vmCore += "local _env=_T(_g)=='table'and setmetatable({},{__index=_g})or _G "
    vmCore += "local _rg=_T(rawget)=='function'and rawget or function(t,k)return _T(t)=='table'and t[k]or nil end "
    vmCore += "local _ls=_rg(_g,_lsk)or _rg(_fenv,_lsk)or _rg(_G,_lsk)or loadstring "
    vmCore += "if _T(_ls)=='function' and _T(_e)=='string' and #_e>0 then "
    vmCore += "local _ok,_res=_T(pcall)=='function'and pcall(_ls,_e)or true,_ls(_e) "
    vmCore += "if _ok and _T(_res)=='function' then "
    vmCore += "if _T(setfenv)=='function' and _T(pcall)=='function' then pcall(setfenv,_res,_env)end "
    vmCore += "if _T(pcall)=='function' then pcall(_res)else _res()end end end "
    return vmCore

def buildSingleVM(innerCode: str, handlerCount: int, pool_tags) -> str:
    style = random.choice(["metatable", "ifchain", "cff"])
    DISPATCH = randomName()
    STORE = randomName()
    MT = randomName()
    out = f"local {STORE}={{}}local {MT}={{__index=function(t,k)return {STORE}[k]end,__metatable='locked'}}local {DISPATCH}=setmetatable({{}},{MT}) "
    realIdx = random.randint(0, handlerCount - 1)
    handlers = []
    for i in range(handlerCount):
        if i == realIdx:
            handlers.append(f"{STORE}[{i+1}]=function(lM){generateSingleJunkLine(pool_tags)}{innerCode}end")
        else:
            handlers.append(f"{STORE}[{i+1}]=function(lM){generateSingleJunkLine()}return nil end")
    random.shuffle(handlers)
    out += " ".join(handlers) + " "

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

def buildMultiVM(payloadStr: str, pool_tags, layers: int = 2) -> str:
    vm = buildTrueVM(payloadStr, pool_tags)
    for _ in range(layers):
        vm = buildSingleVM(vm, 3, pool_tags)
    return vm

def buildStackObfuscation(code: str, pool_tags) -> str:
    nested = code
    for _ in range(2):
        tag_chk = ""
        if pool_tags:
            t = lua_quote(random.choice(pool_tags))
            tag_chk = f"if _T(_RT)~='table' or _RT[{t}]~=true then _er('Moonslot detect you',0)end "
        nested = f"(function()if _T(pcall)=='function'then pcall(function(){tag_chk}{nested}end)else {tag_chk}{nested}end end)();"
    return nested

def getExtraProtections(pool_tags) -> str:
    checks = "\n".join(
        f'    if type(_RT) ~= "table" or _RT[{lua_quote(tag)}] ~= true then error("Moonslot detect you", 0) end'
        for tag in pool_tags
    )
    return f"""
if type(pcall) == "function" then
    pcall(function()
{checks}
        if math.floor(1.5) ~= 1 then error("Moonslot detect you", 0) end
        if string.len("a") ~= 1 then error("Moonslot detect you", 0) end
        local t = setmetatable({{}}, {{__metatable = "locked"}})
        if getmetatable(t) ~= "locked" then error("Moonslot detect you", 0) end
    end)
end
"""

def build22kBlock(pool_tags) -> str:
    tbl = randomName()
    soup = [f"local {tbl}={{}}"]
    target_chars = 6800
    while len("".join(soup)) < target_chars:
        tag = lua_quote(random.choice(pool_tags))
        v = randomName()
        k_idx = random.randint(1, 9999)
        sval = "".join(random.choice(_BASE36) for _ in range(random.randint(14, 34)))
        mode = random.randint(0, 3)
        if mode == 0:
            item = f"if {generate_opaque_predicate()}then if _RT and _RT[{tag}]==nil then _er('Moonslot detect you',0)end {tbl}[{k_idx}]='{sval}' end"
        elif mode == 1:
            item = f"local {v}='{sval}' if _RT and _RT[{tag}]==nil then _er('Moonslot detect you',0)end {tbl}[{k_idx}]={v}"
        elif mode == 2:
            item = f"do local {v}={random.randint(1,999)} if _RT and _RT[{tag}]==nil then _er('Moonslot detect you',0)end {tbl}[{k_idx}]='{sval}' end"
        else:
            item = f"if {generate_opaque_predicate()}then {tbl}[{k_idx}]='{sval}' end"
        soup.append(item)
    random.shuffle(soup[1:])
    soup.append(f"{tbl}=nil ")
    return "".join(soup)

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
                    j += 2
                    continue
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

def obfuscate(sourceCode: str, seed: int = 0, repeat_22k: int = 2) -> str:
    if not sourceCode:
        return '--ERROR'
    random.seed(seed)

    pool_count = 20
    pool_tags = [generate_pool_tag() for _ in range(pool_count)]
    pool_list_lua = "{" + ",".join(lua_quote(t) for t in pool_tags) + "}"
    reg_pools = " ".join(
        f"if _T(_RT)=='table'then _RT[{lua_quote(tag)}]=true end"
        for tag in pool_tags
    )

    minified_user_code = minify_payload(sourceCode)
    obfuscated_user_code = obfuscate_identifiers(minified_user_code)

    at_core = ANTI_TAMPER_CORE.replace("__POOL_LIST_PLACEHOLDER__", pool_list_lua)
    antiDebug = "local _t=os.clock()for _=1,120000 do end if os.clock()-_t>5.0 then while true do if task and _T(task.wait)=='function'then task.wait(0.1)end end end "
    extraProts = getExtraProtections(pool_tags)

    final_user_script = buildMultiVM(obfuscated_user_code, pool_tags, layers=2)
    final_user_script = buildStackObfuscation(final_user_script, pool_tags)

    protection_payload = antiDebug + "\n" + extraProts + "\n" + at_core
    protection_payload = minify_payload(protection_payload)
    anti_tamper_final = buildMultiVM(protection_payload, pool_tags, layers=2)

    filler_22k = "".join(build22kBlock(pool_tags) for _ in range(max(1, repeat_22k)))

    final_code = (
        f"{BOOTSTRAP_HELPERS}"
        f"local _mc={{}}for i=1,400 do _mc[i]=_rp('X',24)end _mc=nil "
        f"if _T(collectgarbage)=='function'then if _T(pcall)=='function'then pcall(collectgarbage)else collectgarbage()end end "
        f"{reg_pools} "
        f"{filler_22k}"
        f"{anti_tamper_final} "
        f"{final_user_script}"
    )

    return HEADER + minify_payload(final_code)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--output', default='obfuscated.lua')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--repeat-22k', type=int, default=2)

    args, _ = ap.parse_known_args()

    try:
        with open(args.input, encoding='utf-8') as f:
            src = f.read()
        out = obfuscate(src, seed=args.seed, repeat_22k=args.repeat_22k)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(out)
    except Exception as e:
        print(f"Error interno: {e}")
        exit(1)

if __name__ == '__main__':
    main()
