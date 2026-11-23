import re
import random
import argparse

HEADER = '''--[[ This code is protected by moonslot 1.01v if you want protect your code whit real obfuscation go to https://discord.gg/ZMnTeuTZ5
]]\n'''

ANCHOR_SYMBOLS = list("@#€_&-+()/*:;!?")
ALERT_BYTES = "77,111,111,110,115,108,111,116,32,100,101,116,101,99,116,32,121,111,117"
_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"
OPCODE_VARS = ["dr", "mn", "et", "gh", "ty", "ui", "op", "vu", "bn", "jg", "ka", "yh"]
POOL_COUNT = 8


def hidden_alert_call() -> str:
    return f"if _T(_er)=='function'then _er(_ch({ALERT_BYTES}),0)end "


def generate_pool_tag() -> str:
    suffix = "".join(random.choice(ANCHOR_SYMBOLS) for _ in range(5))
    return f"[pool.a.d.d.{suffix}]"


def lua_quote(s: str) -> str:
    escaped = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
    )
    return f'"{escaped}"'


def _decode_lua_string_literal(val: str) -> str | None:
    if len(val) < 2 or val[0] not in ('"', "'") or val[-1] != val[0]:
        return None
    body = val[1:-1]
    out_chars = []
    i = 0
    n = len(body)
    escape_map = {
        "a": "\a",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
        "\\": "\\",
        '"': '"',
        "'": "'",
    }
    while i < n:
        ch = body[i]
        if ch != "\\":
            out_chars.append(ch)
            i += 1
            continue
        i += 1
        if i >= n:
            return None
        esc = body[i]
        if esc in escape_map:
            out_chars.append(escape_map[esc])
            i += 1
        elif esc.isdigit():
            digits = esc
            i += 1
            while i < n and len(digits) < 3 and body[i].isdigit():
                digits += body[i]
                i += 1
            code_val = int(digits)
            if code_val > 255:
                return None
            out_chars.append(chr(code_val))
        else:
            out_chars.append(esc)
            i += 1
    return "".join(out_chars)


def encode_lua_string(s: str) -> str:
    """Codifica una cadena en bytes decimales con clave XOR aleatoria y decodificador en tiempo de ejecución."""
    raw = s.encode("utf-8")
    if not raw:
        return "''"
    key = random.randint(17, 239)
    encoded_bytes = ",".join(str(b ^ key) for b in raw)
    return f"(function()local _s=''for _,_b in ipairs({{{encoded_bytes}}})do _s=_s.._ch(_bx(_b,{key}))end return _s end)()"


def obfuscate_number(n: int) -> str:
    """Reemplaza un literal numérico entero por una expresión aritmética ofuscada."""
    mode = random.randint(0, 3)
    if mode == 0:
        a = random.randint(10, 999)
        b = a - n
        return f"({a}-{b})"
    elif mode == 1:
        k = random.randint(2, 9)
        rem = n % k
        q = (n - rem) // k
        if rem == 0:
            return f"({q}*{k})"
        return f"({q}*{k}+{rem})"
    elif mode == 2:
        delta = random.randint(1, 250)
        return f"({n + delta}-{delta})"
    else:
        x = random.randint(1, 120)
        return f"(_bx({n ^ x},{x}))"


BOOTSTRAP_HELPERS = (
    "local _T=type "
    "local _bx=(type(bit32)=='table'and type(bit32.bxor)=='function')and bit32.bxor or function(a,b)"
    "local r,p=0,1 while a>0 or b>0 do if(a%2)~=(b%2)then r=r+p end a=math.floor(a/2)b=math.floor(b/2)p=p*2 end return r end "
    "local _ch=(type(string)=='table'and type(string.char)=='function')and string.char or function(x)return''end "
    "local _by=(type(string)=='table'and type(string.byte)=='function')and string.byte or function(s,i)return 0 end "
    "local _rp=(type(string)=='table'and type(string.rep)=='function')and string.rep or function(s,n)local o=''for _=1,n do o=o..s end return o end "
    "local _tc=(type(table)=='table'and type(table.concat)=='function')and table.concat or function(t)return table.concat and table.concat(t)or''end "
    "local _ti=(type(table)=='table'and type(table.insert)=='function')and table.insert or function(t,v)t[#t+1]=v end "
    "local _fl=(type(math)=='table'and type(math.floor)=='function')and math.floor or function(x)return x-(x%1)end "
    "local _rn=(type(math)=='table'and type(math.random)=='function')and math.random or function(a,b)return a or 0 end "
    "local _er=type(error)=='function'and error or function()end "
    "local _RT=(getgenv and _T(getgenv)=='function')and getgenv()or _G "
    "local _b64d=function(data)"
    "local b='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'"
    "data=string.gsub(data,'[^'..b..'=]','')"
    "return(data:gsub('.',function(x)"
    "if x=='=' then return''end "
    "local r,f='',(b:find(x,1,true)-1)"
    "for i=6,1,-1 do r=r..(f%2^i-f%2^(i-1)>0 and '1' or '0')end return r "
    "end):gsub('%d%d%d?%d?%d?%d?%d?%d?',function(x)"
    "if #x~=8 then return''end "
    "local c=0 for i=1,8 do c=c+(x:sub(i,i)=='1' and 2^(8-i) or 0)end return _ch(c)end))"
    "end "
    "local _DT={} "
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
    if type(_root) == "table" then
        _root._tampered = true
    end
    if type(error) == "function" then
        error(_msg, 0)
    end
end

local function _has_pool(key)
    if type(_root) == "table" and _root[key] == true then
        return true
    end
    if type(_G) == "table" and _G[key] == true then
        return true
    end
    return false
end

local function _check_pools()
    if type(_pool_list) ~= "table" or #_pool_list < 8 then
        _dtc()
    end
    for _, key in ipairs(_pool_list) do
        if not _has_pool(key) then
            _dtc()
        end
    end
end

local function _check_spy_and_loggers()
    _safe_call(function()
        if type(_root) == "table" then
            if type(rawget) == "function" and rawget(_root, "Spy") ~= nil then
                _dtc()
            end
            for k, v in pairs(_root) do
                local ks = tostring(k):lower()
                if type(v) == "function" and (ks:find("spy", 1, true) or ks:find("remotespy", 1, true) or ks:find("httplog", 1, true)) then
                    _dtc()
                end
            end
        end
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
        if type(getgenv) == "function" then
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
                    if d <= 0.0001 or (type(_root) == "table" and _root.math ~= nil and type(_root.math) ~= "table") then
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


def randomName(used_names: set[str] | None = None) -> str:
    while True:
        cand = (
            "_"
            + random.choice("abcdefghijklmnopqrstuvwxyz")
            + "".join(random.choice(_BASE36) for _ in range(random.randint(1, 3)))
            + str(random.randint(0, 99))
        )
        if not used_names or cand not in used_names:
            if used_names is not None:
                used_names.add(cand)
            return cand


def generate_opaque_predicate() -> str:
    r = random.randint(1, 99)
    return f"(_bx({r},{r})==0)"


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
        guarded = f"if _T(_RT)=='table' and _RT[{tag}]~=true then _tampered=true {hidden_alert_call()} end "
        soup.append(f"if {pred} then {guarded}local {v}='{sval}' {tbl}[{k_idx}]={v} end ")
    soup.append(f"{tbl}=nil ")
    return "".join(soup)


def _tokenize_lua(code: str):
    tokens = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if c == "-" and i + 1 < n and code[i + 1] == "-":
            if i + 3 < n and code[i + 2] == "[":
                m = re.match(r'--\[(=*)\[', code[i:])
                if m:
                    eq = m.group(1)
                    close = "]" + eq + "]"
                    j = code.find(close, i + len(m.group(0)))
                    if j != -1:
                        tokens.append(("comment", code[i:j + len(close)]))
                        i = j + len(close)
                        continue
            j = code.find("\n", i)
            if j == -1:
                tokens.append(("comment", code[i:]))
                i = n
            else:
                tokens.append(("comment", code[i:j]))
                i = j
        elif c in '"\'':
            quote = c
            j = i + 1
            while j < n:
                if code[j] == "\\":
                    j += 2
                    continue
                if code[j] == quote:
                    break
                j += 1
            end_idx = min(j + 1, n)
            tokens.append(("str", code[i:end_idx]))
            i = end_idx
        elif c == "[":
            m = re.match(r'\[(=*)\[', code[i:])
            if m:
                eq = m.group(1)
                close = "]" + eq + "]"
                j = code.find(close, i + len(m.group(0)))
                if j != -1:
                    tokens.append(("str", code[i:j + len(close)]))
                    i = j + len(close)
                    continue
            tokens.append(("sym", c))
            i += 1
        elif c.isspace():
            tokens.append(("ws", c))
            i += 1
        elif c.isdigit():
            j = i
            has_dot = False
            while j < n and (code[j].isdigit() or (code[j] == "." and not has_dot and j + 1 < n and code[j + 1].isdigit())):
                if code[j] == ".":
                    has_dot = True
                j += 1
            tokens.append(("num", code[i:j]))
            i = j
        elif c.isalnum() or c == "_":
            j = i
            while j < n and (code[j].isalnum() or code[j] == "_"):
                j += 1
            tokens.append(("ident", code[i:j]))
            i = j
        else:
            tokens.append(("sym", c))
            i += 1
    return tokens


def obfuscate_identifiers(code: str) -> str:
    keywords = {
        "and", "break", "do", "else", "elseif", "end", "false", "for", "function",
        "if", "in", "local", "nil", "not", "or", "repeat", "return", "then", "true",
        "until", "while", "pcall", "type", "math", "string", "table", "bit32",
        "game", "task", "loadstring", "load", "getfenv", "getgenv", "setfenv", "debug",
        "ipairs", "pairs", "next", "tostring", "rawget", "rawset", "setmetatable",
        "getmetatable", "typeof", "coroutine", "buffer", "os", "Instance", "workspace",
        "clonefunction", "hookfunction", "collectgarbage", "gethui", "UDim2", "Color3",
        "_G", "_RT", "_DT", "_b64d", "_tampered", "Spy",
        "_T", "_bx", "_ch", "_by", "_rp", "_tc", "_ti", "_fl", "_rn", "_er",
    }
    keywords.update(OPCODE_VARS)
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
        mapping[v] = randomName(used_names)

    if not mapping:
        return code

    out = []
    for idx, (kind, val) in enumerate(tokens):
        if kind == "ident" and val in mapping:
            prev_sym = ""
            for p in range(idx - 1, -1, -1):
                if tokens[p][0] not in ("ws", "comment"):
                    prev_sym = tokens[p][1]
                    break
            if prev_sym not in (".", ":"):
                out.append(mapping[val])
                continue
        out.append(val)
    return "".join(out)


def obfuscate_strings_and_numbers(code: str, encrypt_strings: bool = True, obfuscate_nums: bool = True) -> str:
    """Cifra cadenas literales (excepto claves de tabla directas) y ofusca constantes numéricas enteras."""
    tokens = _tokenize_lua(code)
    out = []
    for idx, (kind, val) in enumerate(tokens):
        if kind == "str" and encrypt_strings:
            next_tok = ""
            for n_idx in range(idx + 1, len(tokens)):
                if tokens[n_idx][0] not in ("ws", "comment"):
                    next_tok = tokens[n_idx][1]
                    break
            prev_tok = ""
            for p_idx in range(idx - 1, -1, -1):
                if tokens[p_idx][0] not in ("ws", "comment"):
                    prev_tok = tokens[p_idx][1]
                    break

            if prev_tok == "[" and next_tok == "]":
                out.append(val)
                continue

            decoded = _decode_lua_string_literal(val)
            if decoded is not None and 0 < len(decoded) <= 128:
                out.append(encode_lua_string(decoded))
                continue
            out.append(val)
        elif kind == "num" and obfuscate_nums:
            prev_tok = ""
            for p_idx in range(idx - 1, -1, -1):
                if tokens[p_idx][0] not in ("ws", "comment"):
                    prev_tok = tokens[p_idx][1]
                    break
            if "." not in val and val.isdigit() and prev_tok not in (".", ":"):
                n = int(val)
                if 0 <= n <= 5000:
                    out.append(obfuscate_number(n))
                    continue
            out.append(val)
        else:
            out.append(val)
    return "".join(out)


def minify_payload(code: str) -> str:
    code = re.sub(r"--\[\[.*?\]\]", "", code, flags=re.DOTALL)
    code = re.sub(r"--[^\n]*", "", code)

    tokens = _tokenize_lua(code)
    meaningful = [(k, v) for (k, v) in tokens if k not in ("ws", "comment")]

    block_keywords = {"local", "function", "return", "then", "do", "else", "elseif", "end", "until", "in"}

    out = []
    for idx, (kind, tok) in enumerate(meaningful):
        out.append(tok)
        if idx < len(meaningful) - 1:
            _, nxt = meaningful[idx + 1]
            left_word = tok[-1].isalnum() or tok[-1] == "_"
            right_word = nxt[0].isalnum() or nxt[0] == "_"
            if (left_word and right_word) or (
                tok in block_keywords
                and nxt not in (";", ",", ")", "]", "}")
            ):
                out.append(" ")
    return "".join(out).strip()


def flatten_control_flow(statements: list[str]) -> str:
    """Envuelve una lista de sentencias en una máquina de estados con while y dispatch table."""
    if not statements:
        return ""
    state_var = randomName()
    dispatch_tbl = randomName()
    states = [random.randint(1000, 99999) for _ in range(len(statements) + 1)]
    shuffled_indices = list(range(len(statements)))
    random.shuffle(shuffled_indices)

    end_state = states[-1]
    state_to_next = {}
    for pos, stmt_idx in enumerate(shuffled_indices):
        cur_s = states[pos]
        nxt_s = states[pos + 1] if pos + 1 < len(shuffled_indices) else end_state
        state_to_next[cur_s] = (statements[stmt_idx], nxt_s)

    init_state = states[0]
    entries = []
    for s_id, (stmt, nxt_id) in state_to_next.items():
        entries.append(f"[{s_id}]=function() {stmt} {state_var}={nxt_id} end")

    return (
        f"local {state_var}={init_state} "
        f"local {dispatch_tbl}={{{','.join(entries)}}} "
        f"while {state_var}~={end_state} do "
        f"local _fn={dispatch_tbl}[{state_var}] "
        f"if _T(_fn)=='function' then _fn() else {state_var}={end_state} end "
        f"end "
    )


def getExtraProtections(pool_tags) -> str:
    checks = "\n".join(
        f'    if type(_RT) == "table" and _RT[{lua_quote(tag)}] ~= true and (type(_G) ~= "table" or _G[{lua_quote(tag)}] ~= true) then if type(error) == "function" then error(string.char({ALERT_BYTES}), 0) end end'
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


def buildVMBlock(payloadStr: str, pool_tags) -> str:
    """Bucle principal de ejecución de instrucciones de la VM con despacho de opcodes."""
    v_dr, v_mn, v_et, v_gh, v_ty, v_ui, v_op, v_vu, v_bn, v_jg, v_ka, v_yh = OPCODE_VARS

    op_chunk = random.randint(10, 80)
    op_nop = random.randint(81, 160)
    op_end = random.randint(161, 240)

    chunk_size = 48
    parts = [payloadStr[i:i + chunk_size] for i in range(0, len(payloadStr), chunk_size)]

    inst = []
    for part in parts:
        if random.random() < 0.12:
            inst.append(f"{{{v_mn},0}}")
        inst.append(f"{{{v_dr},{lua_quote(part)}}}")
    inst.append(f"{{{v_et},0}}")

    POOL_REF = randomName()
    CHK_TAG = lua_quote(random.choice(pool_tags))
    OP_MAP = randomName()

    vm = (
        f"local {v_dr}={op_chunk} local {v_mn}={op_nop} local {v_et}={op_end} "
        f"local {v_gh}=1 local {v_ty}={{}} local {v_ui}=0 local {v_op}=0 local {v_vu}=nil "
        f"local {v_bn}=_T(_RT)=='table' and _RT or _G "
        f"local {v_jg}={CHK_TAG} "
        f"local {v_ka}={{[{v_dr}]={v_dr},[{v_mn}]={v_mn},[{v_et}]={v_et}}} "
        f"local {v_yh}={{{','.join(inst)}}} "
        f"local {POOL_REF}={v_bn} "
        f"if _T({POOL_REF})=='table' and {POOL_REF}[{v_jg}]==nil then {hidden_alert_call()} end "
        f"while {v_gh}<=#{v_yh} do "
        f"if _T({POOL_REF})=='table' and {POOL_REF}[{v_jg}]~=true then {hidden_alert_call()} break end "
        f"local {OP_MAP}={v_yh}[{v_gh}] "
        f"{v_op},{v_vu}={OP_MAP}[1],{OP_MAP}[2] "
        f"if {v_op}=={v_ka}[{v_dr}] and _T({v_vu})=='string' then "
        f"_ti({v_ty},{v_vu}) {v_ui}={v_ui}+1 "
        f"elseif {v_op}=={v_ka}[{v_et}] then break end "
        f"{v_gh}={v_gh}+1 end "
        f"local _src=_tc({v_ty}) {v_ty}=nil "
    )

    ls_chars = ",".join(str(ord(c)) for c in "loadstring")
    vm += (
        f"if _T({POOL_REF})=='table' and {POOL_REF}[{v_jg}]==true and _T(_src)=='string' and #_src>0 then "
        f"local _lk=_ch({ls_chars}) "
        f"local _fn=(_T({POOL_REF})=='table' and _T({POOL_REF}[_lk])=='function' and {POOL_REF}[_lk])"
        f"or (_T(loadstring)=='function' and loadstring)"
        f"or (_T({POOL_REF})=='table' and _T({POOL_REF}.load)=='function' and {POOL_REF}.load)"
        f"or (_T(load)=='function' and load)or nil "
        f"if _T(_fn)=='function' then "
        f"local _ok,_chunk=pcall(_fn,_src) "
        f"if _ok and _T(_chunk)=='function' then "
        f"local _runOk,_runErr=pcall(_chunk) "
        f"if not _runOk and type(warn)=='function' then warn('[MOONSLOT RUN ERR]: '..tostring(_runErr)) end "
        f"elseif not _ok and type(warn)=='function' then warn('[MOONSLOT LOAD ERR]: '..tostring(_chunk)) end "
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
            if val == "(":
                depth_paren += 1
            elif val == ")":
                depth_paren -= 1
            elif val == "[":
                depth_bracket += 1
            elif val == "]":
                depth_bracket -= 1
            elif val == "{":
                depth_brace += 1
            elif val == "}":
                depth_brace -= 1
    if depth_paren != 0 or depth_bracket != 0 or depth_brace != 0:
        raise ValueError(
            f"Unbalanced delimiters: ()={depth_paren}, []={depth_bracket}, {{}}={depth_brace}"
        )


def wrap_final_code(code: str, pool_tags) -> str:
    """Envuelve el código final sincronizando los 8 pools en _RT y _G antes de validar."""
    v_fn = randomName()
    v_runner = randomName()
    v_guard = randomName()
    v_init = randomName()
    v_chk = randomName()
    v_root_ref = randomName()

    pool_init = " ".join(
        f"if type({v_root_ref})=='table' then {v_root_ref}[{lua_quote(tag)}]=true end "
        f"if type(_G)=='table' then _G[{lua_quote(tag)}]=true end "
        for tag in pool_tags
    )
    pool_checks = " ".join(
        f"if (type({v_root_ref})~='table' or {v_root_ref}[{lua_quote(tag)}]~=true) and (type(_G)~='table' or _G[{lua_quote(tag)}]~=true) then "
        f"if type(error)=='function'then error(string.char({ALERT_BYTES}),0)end end "
        for tag in pool_tags
    )

    init_and_check = (
        f"local function {v_init}() "
        f"local {v_root_ref}=(getgenv and type(getgenv)=='function')and getgenv()or _G "
        f"{pool_init}"
        f"end "
        f"local function {v_chk}() "
        f"local {v_root_ref}=(getgenv and type(getgenv)=='function')and getgenv()or _G "
        f"{pool_checks}"
        f"if type(debug)=='table' and type(debug.gethook)=='function' then "
        f"local _ok,_hk=pcall(debug.gethook) "
        f"if _ok and _hk~=nil then "
        f"if type(error)=='function'then error(string.char({ALERT_BYTES}),0)end "
        f"end "
        f"end "
        f"if type(print)=='function' and type(tostring)=='function' then "
        f"local _ps=tostring(print) "
        f"if type(_ps)=='string' and _ps:match('^function: 0x0000') then "
        f"if type(error)=='function'then error(string.char({ALERT_BYTES}),0)end "
        f"end "
        f"end "
        f"end "
    )

    wrapper = (
        f"local {v_guard}=false "
        f"{init_and_check}"
        f"local function {v_fn}() "
        f"if {v_guard} then return end "
        f"{v_guard}=true "
        f"{v_init}() "
        f"{v_chk}() "
        f"{code} "
        f"end "
        f"local {v_runner}=function() return {v_fn}() end "
        f"{v_runner}()"
    )
    return minify_payload(wrapper)


def obfuscate(sourceCode: str, seed: int = 0, repeat_22k: int = 2) -> str:
    if not sourceCode:
        return "--ERROR"
    random.seed(seed)

    pool_tags = [generate_pool_tag() for _ in range(POOL_COUNT)]
    pool_list_lua = "{" + ",".join(lua_quote(t) for t in pool_tags) + "}"

    minified_user_code = minify_payload(sourceCode)
    obfuscated_user_code = obfuscate_identifiers(minified_user_code)
    obfuscated_user_code = obfuscate_strings_and_numbers(
        obfuscated_user_code, encrypt_strings=True, obfuscate_nums=True
    )

    at_core = minify_payload(ANTI_TAMPER_CORE.replace("__POOL_LIST_PLACEHOLDER__", pool_list_lua))
    extra_prots = minify_payload(getExtraProtections(pool_tags))
    filler_22k = "".join(build22kBlock(pool_tags) for _ in range(max(1, repeat_22k)))

    reg_statements = [
        f"if _T(_RT)=='table'then _RT[{lua_quote(tag)}]=true end if type(_G)=='table'then _G[{lua_quote(tag)}]=true end"
        for tag in pool_tags
    ]
    flattened_reg = flatten_control_flow(reg_statements)

    vm_prot = buildVMBlock(extra_prots + " " + at_core, pool_tags)
    vm_user = buildVMBlock(obfuscated_user_code, pool_tags)

    final_code = (
        f"{BOOTSTRAP_HELPERS}"
        f"local _mc={{}}for i=1,360 do _mc[i]=_rp('X',24)end _mc=nil "
        f"if _T(collectgarbage)=='function'then if _T(pcall)=='function'then pcall(collectgarbage)else collectgarbage()end end "
        f"{flattened_reg} "
        f"{filler_22k}"
        f"{vm_prot} "
        f"{vm_user}"
    )

    wrapped_code = wrap_final_code(minify_payload(final_code), pool_tags)
    result = HEADER + wrapped_code
    validate_generated_lua(result)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default="obfuscated.lua")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--repeat-22k", type=int, default=2)

    args, _ = ap.parse_known_args()

    try:
        with open(args.input, encoding="utf-8") as f:
            src = f.read()
        out = obfuscate(src, seed=args.seed, repeat_22k=args.repeat_22k)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
    except Exception as e:
        print(f"Error interno: {e}")
        exit(1)


if __name__ == "__main__":
    main()
