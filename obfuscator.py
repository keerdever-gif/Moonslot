import re
import random
import argparse

HEADER = '''--[[
  Protected by Moonslot - Extreme Obfuscation
  Unauthorized reproduction or distribution is prohibited.
]]\n'''

ANCHOR_SYMBOLS = list("@#€_&-+()/*:;!?")
ALERT_BYTES = "77,111,111,110,115,108,111,116,32,100,101,116,101,99,116,32,121,111,117"
_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"

def hidden_alert_call() -> str:
    return f"if _T(_er)=='function'then _er(_ch({ALERT_BYTES}),0)end "

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
local _tampered = false
local _pool_list = __POOL_LIST_PLACEHOLDER__
local _root = (getgenv and type(getgenv) == "function") and getgenv() or _G
local _msg = (type(string) == "table" and type(string.char) == "function") and string.char(77,111,111,110,115,108,111,116,32,100,101,116,101,99,116,32,121,111,117) or "err"

local function _safe_call(fn, ...)
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
    if type(error) == "function" then
        error(_msg, 0)
    end
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

local function _check_spy_and_loggers()
    if type(_root) == "table" then
        if type(rawget) == "function" and rawget(_root, "Spy") ~= nil then
            _dtc()
        end
        for k, v in pairs(_root) do
            local ks = tostring(k):lower()
            if type(v) == "function" and (ks:find("spy", 1, true) or ks:find("logger", 1, true) or ks:find("remotespy", 1, true) or ks:find("httplog", 1, true) or ks:find("hook", 1, true) or ks:find("detour", 1, true)) then
                _dtc()
            end
        end
    end
    _safe_call(function()
        if _G and type(rawget) == "function" and rawget(_G, "Spy") ~= nil then
            _dtc()
        end
    end)
end

local function _check_print_and_debug()
    if type(print) == "function" and type(tostring) == "function" then
        local ps = tostring(print)
        if type(ps) == "string" and ps:match("^function: 0x0000") then
            _dtc()
        end
    end
    if type(debug) == "table" and type(debug.gethook) == "function" then
        local ok, hk = _safe_call(debug.gethook)
        if ok and hk ~= nil then
            _dtc()
        end
    end
    _safe_call(function()
        if type(debug) == "table" and type(debug.getinfo) == "function" then
            local info = debug.getinfo(function() end, "u")
            if type(info) ~= "table" or info.nups == nil then
                _dtc()
            end
        end
    end)
end

local function _check_string_char_and_buffer()
    local okChar, resChar = _safe_call(string.char, nil)
    if okChar and resChar == "" then
        _dtc()
    end
    if type(buffer) == "table" and type(buffer.fromstring) == "function" then
        _safe_call(function()
            local str = "moonslot_env_check"
            local buf = buffer.fromstring(str)
            local okSvc, svc = _safe_call(function() return game:GetService("EncodingService") end)
            if okSvc and type(typeof) == "function" and typeof(svc) == "Instance" then
                local okComp, comp = _safe_call(function()
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
    local ok = _safe_call(function()
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
    _safe_call(function()
        local a = game:GetService("Players")
        local b = game:GetService("Players")
        if a ~= b then
            _dtc()
        end
    end)
    _safe_call(function()
        local obj = Instance.new("Part")
        obj.Parent = workspace
        obj:Destroy()
        if obj.Parent ~= nil then
            _dtc()
        end
    end)
    _safe_call(function()
        local s = Instance.new("Sound")
        local okLoud = _safe_call(function() s.PlaybackLoudness = 5 end)
        if okLoud then
            s:Destroy()
            _dtc()
        end
        s:Destroy()
    end)
end

local function _check_debug_constants_and_hooks()
    _safe_call(function()
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
                local st = _safe_call(debug.setconstant, probeFn, idx, "dog")
                if st and probeFn() == "dog" then
                    _dtc()
                end
            end
        end
    end)
    _safe_call(function()
        if type(clonefunction) == "function" and type(hookfunction) == "function" then
            local function probeA() return 1 end
            local ca = clonefunction(probeA)
            local st = _safe_call(hookfunction, probeA, function() return 2 end)
            if st and probeA() == 2 and ca() == 1 then
                _dtc()
            end
        end
    end)
end

local function _check_timing_and_env()
    _safe_call(function()
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

_safe_call(_check_pools)
_safe_call(_check_spy_and_loggers)
_safe_call(_check_print_and_debug)
_safe_call(_check_string_char_and_buffer)
_safe_call(_check_server_service)
_safe_call(_check_coroutine_and_metatables)
_safe_call(_check_debug_constants_and_hooks)
_safe_call(_check_timing_and_env)
'''

def randomName() -> str:
    return "_" + random.choice("abcdefghijklmnopqrstuvwxyz") + "".join(random.choice(_BASE36) for _ in range(random.randint(1, 3))) + str(random.randint(0, 99))

def generate_opaque_predicate() -> str:
    r = random.randint(1, 99)
    return f"(_bx({r},{r})==0)"

def _tokenize_lua(code: str):
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
            tokens.append(("str", code[i:j+1]))
            i = j + 1
        elif c == '[':
            m = re.match(r'\[(=*)\[', code[i:])
            if m:
                eq = m.group(1)
                close = ']' + eq + ']'
                j = code.find(close, i + len(m.group(0)))
                if j != -1:
                    tokens.append(("str", code[i:j+len(close)]))
                    i = j + len(close)
                    continue
            tokens.append(("sym", c))
            i += 1
        elif c.isspace():
            tokens.append(("ws", c))
            i += 1
        elif c.isalnum() or c == '_':
            j = i
            while j < n and (code[j].isalnum() or code[j] == '_'):
                j += 1
            tokens.append(("ident", code[i:j]))
            i = j
        else:
            tokens.append(("sym", c))
            i += 1
    return tokens

def obfuscate_identifiers(code: str) -> str:
    keywords = {
        'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function',
        'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then', 'true',
        'until', 'while', 'pcall', 'type', 'math', 'string', 'table', 'bit32',
        'game', 'task', 'loadstring', 'load', 'getfenv', 'getgenv', 'setfenv', 'debug',
        'ipairs', 'pairs', 'next', 'tostring', 'rawget', 'rawset', 'setmetatable',
        'getmetatable', 'typeof', 'coroutine', 'buffer', 'os', 'Instance', 'workspace',
        'clonefunction', 'hookfunction', 'collectgarbage', 'gethui', 'UDim2', 'Color3',
        '_G', '_RT', '_tampered', 'Spy', '_T', '_bx', '_ch', '_rp', '_tc', '_ti', '_fl', '_rn', '_er'
    }
    tokens = _tokenize_lua(code)
    local_vars = set()
    used_names = set(keywords)

    for idx, (kind, val) in enumerate(tokens):
        if kind == "ident" and val == "local":
            j = idx + 1
            while j < len(tokens) and tokens[j][0] == "ws":
                j += 1
            if j < len(tokens) and tokens[j][0] == "ident" and tokens[j][1] == "function":
                j += 1
                while j < len(tokens) and tokens[j][0] == "ws":
                    j += 1
            if j < len(tokens) and tokens[j][0] == "ident":
                vname = tokens[j][1]
                if vname not in keywords and len(vname) > 1:
                    local_vars.add(vname)

    mapping = {}
    for v in sorted(local_vars):
        cand = randomName()
        while cand in used_names:
            cand = randomName()
        used_names.add(cand)
        mapping[v] = cand

    if not mapping:
        return code

    out = []
    for idx, (kind, val) in enumerate(tokens):
        if kind == "ident" and val in mapping:
            prev_sym = ""
            for p in range(idx - 1, -1, -1):
                if tokens[p][0] != "ws":
                    prev_sym = tokens[p][1]
                    break
            if prev_sym not in (".", ":"):
                out.append(mapping[val])
                continue
        out.append(val)
    return "".join(out)

def minify_payload(code: str) -> str:
    code = re.sub(r'--\[\[.*?\]\]', '', code, flags=re.DOTALL)
    code = re.sub(r'--[^\n]*', '', code)

    tokens = _tokenize_lua(code)
    meaningful = [(k, v) for (k, v) in tokens if k != "ws"]

    out = []
    for idx, (kind, tok) in enumerate(meaningful):
        out.append(tok)
        if idx < len(meaningful) - 1:
            _, nxt = meaningful[idx + 1]
            left_word = tok[-1].isalnum() or tok[-1] == '_'
            right_word = nxt[0].isalnum() or nxt[0] == '_'
            if (left_word and right_word) or (
                tok in ("end", "then", "do", "else", "break", "return") and nxt not in (";", ",", ")", "]", "}")
            ):
                out.append(' ')
    return ''.join(out).strip()

def getExtraProtections(pool_tags) -> str:
    checks = "\n".join(
        f'    if type(_RT) == "table" and _RT[{lua_quote(tag)}] ~= true then if type(error) == "function" then error(string.char({ALERT_BYTES}), 0) end end'
        for tag in pool_tags
    )
    return f"""
if type(pcall) == "function" then
    pcall(function()
{checks}
        if math.floor(1.5) ~= 1 and type(error) == "function" then error(string.char({ALERT_BYTES}), 0) end
        if string.len("a") ~= 1 and type(error) == "function" then error(string.char({ALERT_BYTES}), 0) end
        local t = setmetatable({{}}, {{__metatable = "locked"}})
        if getmetatable(t) ~= "locked" and type(error) == "function" then error(string.char({ALERT_BYTES}), 0) end
    end)
end
"""

def build22kBlock(pool_tags) -> str:
    tbl = randomName()
    soup = [f"local {tbl}={{}}"]
    target_chars = 2880
    while len("".join(soup)) < target_chars:
        tag = lua_quote(random.choice(pool_tags))
        v = randomName()
        k_idx = random.randint(1, 9999)
        sval = "".join(random.choice(_BASE36) for _ in range(random.randint(14, 34)))
        pred = generate_opaque_predicate()
        guarded = f"if _T(_RT)=='table' and _RT[{tag}]==nil then _tampered=true {hidden_alert_call()} end "
        soup.append(f"if {pred} then {guarded}local {v}='{sval}' {tbl}[{k_idx}]={v} end ")
    soup.append(f"{tbl}=nil ")
    return "".join(soup)

def buildVMBlock(payloadStr: str, pool_tags) -> str:
    # Solo opcodes (sin ofuscar/cifrar bytes), enlazado con las variables pools
    raw = payloadStr.encode("utf-8")

    op_push = random.randint(10, 80)
    op_nop = random.randint(81, 160)
    op_end = random.randint(161, 240)

    inst = []
    for b in raw:
        if random.random() < 0.12:
            inst.append(f"{{{op_nop},0}}")
        inst.append(f"{{{op_push},{b}}}")
    inst.append(f"{{{op_end},0}}")

    INST_TBL = randomName()
    PC = randomName()
    BUF = randomName()
    OP_V = randomName()
    ARG_V = randomName()
    POOL_REF = randomName()
    CHK_TAG = lua_quote(random.choice(pool_tags))

    vm = (
        f"local {POOL_REF}=_T(_RT)=='table' and _RT or _G "
        f"if _T({POOL_REF})=='table' and {POOL_REF}[{CHK_TAG}]==nil then {hidden_alert_call()} end "
        f"local {INST_TBL}={{{','.join(inst)}}} "
        f"local {BUF}={{}} local {PC}=1 "
        f"while {PC}<=#{INST_TBL} do "
        f"if _T({POOL_REF})=='table' and {POOL_REF}[{CHK_TAG}]~=true then {hidden_alert_call()} break end "
        f"local _ins={INST_TBL}[{PC}] "
        f"local {OP_V}, {ARG_V} = _ins[1], _ins[2] "
        f"if {OP_V}=={op_push} then "
        f"_ti({BUF},_ch({ARG_V})) "
        f"elseif {OP_V}=={op_end} then break end "
        f"{PC}={PC}+1 end "
        f"local _src=_tc({BUF}) {BUF}=nil "
    )

    ls_chars = ",".join(str(ord(c)) for c in "loadstring")
    vm += (
        f"if _T({POOL_REF})=='table' and {POOL_REF}[{CHK_TAG}]==true and _T(_src)=='string' and #_src>0 then "
        f"local _lk=_ch({ls_chars}) "
        f"local _fn=(_T({POOL_REF})=='table' and _T({POOL_REF}[_lk])=='function' and {POOL_REF}[_lk])"
        f"or (_T(loadstring)=='function' and loadstring)"
        f"or (_T({POOL_REF})=='table' and _T({POOL_REF}.load)=='function' and {POOL_REF}.load)"
        f"or (_T(load)=='function' and load)or nil "
        f"if _T(_fn)=='function' then "
        f"local _ok,_chunk=pcall(_fn,_src) "
        f"if _ok and _T(_chunk)=='function' then pcall(_chunk) end "
        f"end "
        f"end "
    )
    return vm

def validate_generated_lua(lua_code: str) -> None:
    tokens = _tokenize_lua(lua_code)
    depth_paren = 0
    depth_bracket = 0
    depth_brace = 0
    for kind, val in tokens:
        if kind == "sym":
            if val == "(": depth_paren += 1
            elif val == ")": depth_paren -= 1
            elif val == "[": depth_bracket += 1
            elif val == "]": depth_bracket -= 1
            elif val == "{": depth_brace += 1
            elif val == "}": depth_brace -= 1
    if depth_paren != 0 or depth_bracket != 0 or depth_brace != 0:
        raise ValueError(f"Unbalanced delimiters: ()={depth_paren}, []={depth_bracket}, {{}}={depth_brace}")

def obfuscate(sourceCode: str, seed: int = 0, repeat_22k: int = 2) -> str:
    if not sourceCode:
        return '--ERROR'
    random.seed(seed)

    pool_count = 18
    pool_tags = [generate_pool_tag() for _ in range(pool_count)]
    pool_list_lua = "{" + ",".join(lua_quote(t) for t in pool_tags) + "}"
    reg_pools = " ".join(
        f"if _T(_RT)=='table'then _RT[{lua_quote(tag)}]=true end"
        for tag in pool_tags
    )

    minified_user_code = minify_payload(sourceCode)
    obfuscated_user_code = obfuscate_identifiers(minified_user_code)

    at_core = minify_payload(ANTI_TAMPER_CORE.replace("__POOL_LIST_PLACEHOLDER__", pool_list_lua))
    extra_prots = minify_payload(getExtraProtections(pool_tags))
    filler_22k = "".join(build22kBlock(pool_tags) for _ in range(max(1, repeat_22k)))

    vm_prot = buildVMBlock(extra_prots + " " + at_core, pool_tags)
    vm_user = buildVMBlock(obfuscated_user_code, pool_tags)

    final_code = (
        f"{BOOTSTRAP_HELPERS}"
        f"local _mc={{}}for i=1,360 do _mc[i]=_rp('X',24)end _mc=nil "
        f"if _T(collectgarbage)=='function'then if _T(pcall)=='function'then pcall(collectgarbage)else collectgarbage()end end "
        f"{reg_pools} "
        f"{filler_22k}"
        f"{vm_prot} "
        f"{vm_user}"
    )

    result = HEADER + minify_payload(final_code)
    validate_generated_lua(result)
    return result

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
