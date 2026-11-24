import re
import random
import argparse

HEADER = '''--[[ This code is protected by moonslot 0.2 if you want protect your code whit real obfuscation go to https://discord.gg/ZMnTeuTZ5
]]\n'''

ANCHOR_SYMBOLS = list("@#€_&-+()/*:;!?")
_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"
OPCODE_VARS = ["dr", "mn", "et", "gh", "ty", "ui", "op", "vu", "bn", "jg", "ka", "yh"]
POOL_COUNT = 8

HEARTBEAT_TEMPLATE = """local RunService = game:GetService("RunService")
local ticks = 0
local total = 0
local connection

connection = RunService.Heartbeat:Connect(function(dt)
    ticks = ticks + 1
    total = total + dt
    if ticks >= 5 then
        connection:Disconnect()
    end
end)
"""


def _str_from_bytes(s: str) -> str:
    raw = s.encode("utf-8")
    if not raw:
        return "''"
    nums = ",".join(str(b) for b in raw)
    return f"string.char({nums})"


def ascii_obfuscate(s: str) -> str:
    """Ofusca una cadena mediante codigos ASCII y expresiones aritmeticas simples."""
    raw = s.encode("utf-8")
    if not raw:
        return "''"
    parts = []
    for b in raw:
        mode = random.randint(0, 2)
        if mode == 0:
            d = random.randint(1, 35)
            parts.append(f"({b + d}-{d})")
        elif mode == 1 and b >= 4:
            k = random.randint(2, 4)
            rem = b % k
            q = b // k
            parts.append(f"({q}*{k}+{rem})" if rem else f"({q}*{k})")
        else:
            parts.append(str(b))
    return f"string.char({','.join(parts)})"


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
    raw = s.encode("utf-8")
    if not raw:
        return "''"
    key = random.randint(17, 239)
    half = max(1, len(raw) // 2)
    b1 = ",".join(str(b ^ key) for b in raw[:half])
    b2 = ",".join(str(b ^ key) for b in raw[half:])

    fn_name = randomName()
    c_fn = randomName()
    x_fn = randomName()
    acc = randomName()
    item = randomName()
    p1 = randomName()
    r_v = randomName()
    bit_v = randomName()

    part2_loop = (
        f"for _,{item} in ipairs({{{b2}}})do {acc}={acc}..{c_fn}({x_fn}({item},{key}))end "
        if b2
        else ""
    )

    return (
        f"(function()local function {fn_name}()"
        f"local {c_fn}=(type(string)=='table'and type(string.char)=='function')and string.char or function()return '' end "
        f"local {x_fn}=(type(bit32)=='table'and type(bit32.bxor)=='function')and bit32.bxor or function(a,b)"
        f"local {r_v},{bit_v}=0,1 while a>0 or b>0 do if(a%2)~=(b%2)then {r_v}={r_v}+{bit_v} end a=math.floor(a/2)b=math.floor(b/2){bit_v}={bit_v}*2 end return {r_v} end "
        f"local {acc}='' "
        f"local {p1}={{{b1}}} "
        f"for _,{item} in ipairs({p1})do {acc}={acc}..{c_fn}({x_fn}({item},{key}))end "
        f"{part2_loop}"
        f"{p1}=nil "
        f"return {acc} end return {fn_name}() end)()"
    )


def obfuscate_number(n: int) -> str:
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


def randomName(used_names: set[str] | None = None) -> str:
    while True:
        cand = (
            "_"
            + random.choice("abcdefghijklmnopqrstuvwxyz")
            + "".join(random.choice(_BASE36) for _ in range(random.randint(2, 4)))
            + str(random.randint(10, 999))
        )
        if not used_names or cand not in used_names:
            if used_names is not None:
                used_names.add(cand)
            return cand


def generate_opaque_predicate() -> str:
    r = random.randint(1, 99)
    return f"(_bx({r},{r})==0)"


def apply_moonveil_style_macros(code: str) -> str:
    """Procesa macros estilo MoonVeil (MS_* y MV_*) antes de ofuscar."""
    code = re.sub(r"\b(?:MS|MV)_OMIT\s*\([^)]*\)\s*;?", "", code)
    code = re.sub(r"\b(?:MS|MV)_OMIT\b[^\n]*", "", code)

    code = re.sub(r"\b(?:MS|MV)_CRASH\s*\(\s*\)", "return", code)

    def _line_repl(match: re.Match) -> str:
        line_no = code[: match.start()].count("\n") + 1
        return obfuscate_number(line_no)

    code = re.sub(r"\b(?:MS|MV)_LINE\s*\(\s*\)", _line_repl, code)

    code = re.sub(
        r"\b(?:MS|MV)_OPAQUE\s*\(\s*([^)]*)\s*\)",
        lambda m: f"({generate_opaque_predicate()} and ({m.group(1).strip() or 'true'}))"
        if m.group(1).strip()
        else generate_opaque_predicate(),
        code,
    )

    code = re.sub(
        r"\b(?:MS|MV)_ASSUME\s*\(\s*([^)]+)\s*\)",
        lambda m: f"if not ({m.group(1).strip()}) then return end",
        code,
    )

    code = re.sub(
        r"\b(?:MS|MV)_PRECHECK\s*\(\s*\)",
        "if type(game)~='userdata' and type(game)~='table' then return end",
        code,
    )

    code = re.sub(
        r"\b(?:MS|MV)_REWRITE\s*\(\s*([^)]+)\s*\)",
        lambda m: f"(function()return ({m.group(1).strip()})end)()",
        code,
    )

    code = re.sub(
        r"\b(?:MS|MV)_ENC_FUNC\s*\(\s*(function\b.*?\bend)\s*\)",
        lambda m: f"(function(...)return ({m.group(1).strip()})(...)end)",
        code,
    )

    def _enc_str_repl(match: re.Match) -> str:
        raw_arg = match.group(1).strip()
        dec = _decode_lua_string_literal(raw_arg)
        if dec is not None:
            return encode_lua_string(dec)
        return raw_arg

    code = re.sub(r"\b(?:MS|MV)_ENC_STR\s*\(\s*([^)]+)\s*\)", _enc_str_repl, code)

    code = re.sub(
        r"\b(?:MS|MV)_INDEX_TO_NUM\s*\(\s*([^,\s]+)\s*,\s*([^)]+)\s*\)",
        lambda m: f"{m.group(1).strip()}[{obfuscate_number(int(m.group(2).strip())) if m.group(2).strip().isdigit() else m.group(2).strip()}]",
        code,
    )

    code = re.sub(
        r"\b(?:MS|MV)_(?:INLINE|VM|CFF|COMPRESS|OBFUSCATED)\s*\(\s*([^)]*)\s*\)",
        lambda m: m.group(1).strip() if m.group(1).strip() else "",
        code,
    )

    code = re.sub(r"\bATTRIBUTE\s*\([^)]*\)", "", code)
    return code


def build_bootstrap_helpers(v_t, v_bx, v_ch, v_by, v_rp, v_tc, v_ti, v_fl, v_rn, v_rt, v_dt) -> str:
    return (
        f"local {v_t}=type "
        f"local {v_bx}=({v_t}(bit32)=='table'and {v_t}(bit32.bxor)=='function')and bit32.bxor or function(a,b)"
        f"local r,p=0,1 while a>0 or b>0 do if(a%2)~=(b%2)then r=r+p end a=math.floor(a/2)b=math.floor(b/2)p=p*2 end return r end "
        f"local {v_ch}=({v_t}(string)=='table'and {v_t}(string.char)=='function')and string.char or function()return''end "
        f"local {v_by}=({v_t}(string)=='table'and {v_t}(string.byte)=='function')and string.byte or function()return 0 end "
        f"local {v_rp}=({v_t}(string)=='table'and {v_t}(string.rep)=='function')and string.rep or function(s,n)local o=''for _=1,n do o=o..s end return o end "
        f"local {v_tc}=({v_t}(table)=='table'and {v_t}(table.concat)=='function')and table.concat or function(t)return table.concat and table.concat(t)or''end "
        f"local {v_ti}=({v_t}(table)=='table'and {v_t}(table.insert)=='function')and table.insert or function(t,v)t[#t+1]=v end "
        f"local {v_fl}=({v_t}(math)=='table'and {v_t}(math.floor)=='function')and math.floor or function(x)return x-(x%1)end "
        f"local {v_rn}=({v_t}(math)=='table'and {v_t}(math.random)=='function')and math.random or function(a)return a or 0 end "
        f"local {v_rt}=(getgenv and {v_t}(getgenv)=='function')and getgenv()or _G "
        f"local {v_dt}={{}} "
    )


def build_anti_tamper_core(pool_list_lua: str) -> str:
    """Anti-env logger y anti-tamper refinado con corrupcion silenciosa y checks solidos."""
    f_flag = randomName()
    f_pools = randomName()
    f_root = randomName()
    f_safe = randomName()
    f_corrupt = randomName()
    f_has = randomName()

    chk_pools = randomName()
    chk_hooks_dbg = randomName()
    chk_meta_coro = randomName()
    chk_env_funs = randomName()
    chk_timing = randomName()

    s_hook_pat = ascii_obfuscate("^function: 0x0000")
    s_info_mode = ascii_obfuscate("u")
    s_c_a = ascii_obfuscate("cat")
    s_c_b = ascii_obfuscate("dog")
    s_math_k = ascii_obfuscate("math")
    s_env_ok = ascii_obfuscate("env_ok")
    s_env_k = ascii_obfuscate("env")
    s_val_k = ascii_obfuscate("val")
    s_junk = ascii_obfuscate("x9z_corrupt")

    return f"""
local {f_flag} = false
local {f_pools} = {pool_list_lua}
local {f_root} = (getgenv and type(getgenv) == "function") and getgenv() or _G

local function {f_safe}(fn, ...)
    if type(fn) ~= "function" then
        return false, nil
    end
    if type(pcall) == "function" then
        return pcall(fn, ...)
    end
    return true, fn(...)
end

local function {f_corrupt}()
    {f_flag} = true
    if type({f_pools}) == "table" then
        for k in pairs({f_pools}) do
            {f_pools}[k] = {s_junk}
        end
    end
end

local function {f_has}(key)
    if type({f_root}) == "table" and {f_root}[key] == true then
        return true
    end
    if type(_G) == "table" and _G[key] == true then
        return true
    end
    return false
end

local function {chk_pools}()
    if {f_flag} then return end
    if type({f_pools}) ~= "table" or #{f_pools} < 8 then
        {f_corrupt}()
        return
    end
    for _, key in ipairs({f_pools}) do
        if not {f_has}(key) then
            {f_corrupt}()
            return
        end
    end
end

local function {chk_hooks_dbg}()
    if {f_flag} then return end
    if type(print) == "function" and type(tostring) == "function" then
        local ps = tostring(print)
        if type(ps) == "string" and ps:match({s_hook_pat}) then
            {f_corrupt}()
            return
        end
    end
    if type(debug) == "table" and type(debug.gethook) == "function" then
        local ok, hk = {f_safe}(debug.gethook)
        if ok and hk ~= nil then
            {f_corrupt}()
            return
        end
    end
    {f_safe}(function()
        if type(debug) == "table" and type(debug.getinfo) == "function" then
            local info = debug.getinfo(function() end, {s_info_mode})
            if type(info) ~= "table" or info.nups == nil then
                {f_corrupt}()
            end
        end
    end)
end

local function {chk_meta_coro}()
    if {f_flag} then return end
    if type(coroutine) == "table" and type(coroutine.create) == "function" and type(coroutine.resume) == "function" then
        local co = coroutine.create(function()
            coroutine.yield(10)
            coroutine.yield(20)
        end)
        local _, v1 = coroutine.resume(co)
        local _, v2 = coroutine.resume(co)
        if v1 ~= 10 or v2 ~= 20 then
            {f_corrupt}()
            return
        end
    end
    local mt = setmetatable({{}}, {{__index = function(_, k) return tostring(k) .. "_ok" end}})
    if mt[{s_env_k}] ~= {s_env_ok} then
        {f_corrupt}()
        return
    end
    local rawT = setmetatable({{}}, {{__newindex = function() end}})
    if type(rawset) == "function" and type(rawget) == "function" then
        rawset(rawT, {s_val_k}, 42)
        if rawget(rawT, {s_val_k}) ~= 42 then
            {f_corrupt}()
        end
    end
end

local function {chk_env_funs}()
    if {f_flag} then return end
    local okChar, resChar = {f_safe}(string.char, nil)
    if okChar and resChar == "" then
        {f_corrupt}()
        return
    end
    {f_safe}(function()
        if type(debug) == "table" and type(debug.getconstants) == "function" and type(debug.setconstant) == "function" then
            local function probeFn()
                local a = {s_c_a}
                return a
            end
            local c = debug.getconstants(probeFn)
            local idx = nil
            if type(c) == "table" then
                for i, v in pairs(c) do
                    if v == {s_c_a} then
                        idx = i
                        break
                    end
                end
            end
            if idx and idx > 0 then
                local st = {f_safe}(debug.setconstant, probeFn, idx, {s_c_b})
                if st and probeFn() == {s_c_b} then
                    {f_corrupt}()
                end
            end
        end
    end)
    {f_safe}(function()
        if type(clonefunction) == "function" and type(hookfunction) == "function" then
            local function probeA() return 1 end
            local ca = clonefunction(probeA)
            local st = {f_safe}(hookfunction, probeA, function() return 2 end)
            if st and probeA() == 2 and ca() == 1 then
                {f_corrupt}()
            end
        end
    end)
end

local function {chk_timing}()
    if {f_flag} then return end
    {f_safe}(function()
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
                    if d <= 0.0001 or (type({f_root}) == "table" and {f_root}[{s_math_k}] ~= nil and type({f_root}[{s_math_k}]) ~= "table") then
                        {f_corrupt}()
                    end
                end
            end
        end
    end)
end

{f_safe}({chk_pools})
{f_safe}({chk_hooks_dbg})
{f_safe}({chk_meta_coro})
{f_safe}({chk_env_funs})
{f_safe}({chk_timing})
if {f_flag} then return end
"""


def build22kBlock(pool_tags, v_t, v_rt) -> str:
    tbl = randomName()
    soup = [f"local {tbl}={{}}"]
    target_chars = 2880
    while len("".join(soup)) < target_chars:
        tag = lua_quote(random.choice(pool_tags))
        v = randomName()
        k_idx = random.randint(1, 9999)
        sval = "".join(random.choice(_BASE36) for _ in range(random.randint(14, 34)))
        pred = generate_opaque_predicate()
        guarded = f"if {v_t}({v_rt})=='table' and {v_rt}[{tag}]~=true then return end "
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


def obfuscate_identifiers(code: str, protected_names: set[str]) -> str:
    keywords = {
        "and", "break", "do", "else", "elseif", "end", "false", "for", "function",
        "if", "in", "local", "nil", "not", "or", "repeat", "return", "then", "true",
        "until", "while", "pcall", "type", "math", "string", "table", "bit32",
        "game", "task", "loadstring", "load", "getfenv", "getgenv", "setfenv", "debug",
        "ipairs", "pairs", "next", "tostring", "rawget", "rawset", "setmetatable",
        "getmetatable", "typeof", "coroutine", "buffer", "os", "Instance", "workspace",
        "clonefunction", "hookfunction", "collectgarbage", "gethui", "UDim2", "Color3",
        "_G", "Enum",
    }
    keywords.update(OPCODE_VARS)
    keywords.update(protected_names)

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
                if len(decoded) <= 12:
                    out.append(ascii_obfuscate(decoded))
                else:
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


def flatten_control_flow(statements: list[str], v_t) -> str:
    if not statements:
        return ""
    state_var = randomName()
    dispatch_tbl = randomName()
    fn_slot = randomName()
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
        f"local {fn_slot}={dispatch_tbl}[{state_var}] "
        f"if {v_t}({fn_slot})=='function' then {fn_slot}() else {state_var}={end_state} end "
        f"end {dispatch_tbl}=nil "
    )


def getExtraProtections(pool_tags) -> str:
    s_mt = ascii_obfuscate("locked")
    s_chk = ascii_obfuscate("a")
    checks = "\n".join(
        f'    if type(getgenv) == "function" and type(getgenv()) == "table" and getgenv()[{lua_quote(tag)}] ~= true and (type(_G) ~= "table" or _G[{lua_quote(tag)}] ~= true) then return end'
        for tag in pool_tags
    )
    return f"""
if type(pcall) == "function" then
    pcall(function()
{checks}
        if math.floor(1.5) ~= 1 then return end
        if string.len({s_chk}) ~= 1 then return end
        local t = setmetatable({{}}, {{__metatable = {s_mt}}})
        if getmetatable(t) ~= {s_mt} then return end
    end)
end
"""


def buildVMBlock(payloadStr: str, pool_tags, v_t, v_ch, v_tc, v_ti, v_rt) -> str:
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

    pool_ref = randomName()
    chk_tag = lua_quote(random.choice(pool_tags))
    op_map = randomName()
    src_var = randomName()
    lk_var = randomName()
    fn_var = randomName()
    ok_var = randomName()
    chunk_var = randomName()
    corrupt_fn = randomName()

    vm = (
        f"local {v_dr}={op_chunk} local {v_mn}={op_nop} local {v_et}={op_end} "
        f"local {v_gh}=1 local {v_ty}={{}} local {v_ui}=0 local {v_op}=0 local {v_vu}=nil "
        f"local {v_bn}={v_t}({v_rt})=='table' and {v_rt} or _G "
        f"local {v_jg}={chk_tag} "
        f"local {v_ka}={{[{v_dr}]={v_dr},[{v_mn}]={v_mn},[{v_et}]={v_et}}} "
        f"local {v_yh}={{{','.join(inst)}}} "
        f"local {pool_ref}={v_bn} "
        f"local function {corrupt_fn}() if {v_t}({v_ty})=='table' then for k in pairs({v_ty})do {v_ty}[k]=nil end end {v_ty}=nil {v_yh}=nil end "
        f"if {v_t}({pool_ref})=='table' and {pool_ref}[{v_jg}]~=true then {corrupt_fn}() return end "
        f"while {v_gh}<=#{v_yh} do "
        f"if {v_t}({pool_ref})=='table' and {pool_ref}[{v_jg}]~=true then {corrupt_fn}() return end "
        f"local {op_map}={v_yh}[{v_gh}] "
        f"{v_op},{v_vu}={op_map}[1],{op_map}[2] "
        f"if {v_op}=={v_ka}[{v_dr}] and {v_t}({v_vu})=='string' then "
        f"{v_ti}({v_ty},{v_vu}) {v_ui}={v_ui}+1 "
        f"elseif {v_op}=={v_ka}[{v_et}] then break end "
        f"{v_gh}={v_gh}+1 end "
        f"local {src_var}={v_tc}({v_ty}) {v_ty}=nil {v_yh}=nil "
    )

    ls_chars = ",".join(str(ord(c)) for c in "loadstring")
    ld_chars = ",".join(str(ord(c)) for c in "load")
    vm += (
        f"if {v_t}({pool_ref})=='table' and {pool_ref}[{v_jg}]==true and {v_t}({src_var})=='string' and #{src_var}>0 then "
        f"local {lk_var}={v_ch}({ls_chars}) "
        f"local {fn_var}=({v_t}({pool_ref})=='table' and {v_t}({pool_ref}[{lk_var}])=='function' and {pool_ref}[{lk_var}])"
        f"or ({v_t}(loadstring)=='function' and loadstring)"
        f"or ({v_t}({pool_ref})=='table' and {v_t}({pool_ref}[{v_ch}({ld_chars})])=='function' and {pool_ref}[{v_ch}({ld_chars})])"
        f"or ({v_t}(load)=='function' and load)or nil "
        f"if {v_t}({fn_var})=='function' then "
        f"local {ok_var},{chunk_var}=pcall({fn_var},{src_var}) "
        f"if {ok_var} and {v_t}({chunk_var})=='function' then pcall({chunk_var}) end "
        f"{chunk_var}=nil "
        f"end "
        f"{src_var}=nil "
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
    v_fn = randomName()
    v_runner = randomName()
    v_guard = randomName()
    v_init = randomName()
    v_chk = randomName()
    v_root_ref = randomName()
    g_key = ascii_obfuscate("_G")
    gv_key = ascii_obfuscate("getgenv")

    pool_init = " ".join(
        f"if type({v_root_ref})=='table' then {v_root_ref}[{lua_quote(tag)}]=true end "
        f"if type(_G)=='table' then _G[{lua_quote(tag)}]=true end "
        for tag in pool_tags
    )
    pool_checks = " ".join(
        f"if (type({v_root_ref})~='table' or {v_root_ref}[{lua_quote(tag)}]~=true) and (type(_G)~='table' or _G[{lua_quote(tag)}]~=true) then return false end "
        for tag in pool_tags
    )

    init_and_check = (
        f"local function {v_init}() "
        f"local {v_root_ref}=({gv_key} and type(_G[{gv_key}])=='function')and _G[{gv_key}]()or _G[{g_key}] or _G "
        f"{pool_init}"
        f"end "
        f"local function {v_chk}() "
        f"local {v_root_ref}=({gv_key} and type(_G[{gv_key}])=='function')and _G[{gv_key}]()or _G[{g_key}] or _G "
        f"{pool_checks}"
        f"if type(debug)=='table' and type(debug.gethook)=='function' then "
        f"local _ok,_hk=pcall(debug.gethook) "
        f"if _ok and _hk~=nil then return false end "
        f"end "
        f"if type(print)=='function' and type(tostring)=='function' then "
        f"local _ps=tostring(print) "
        f"if type(_ps)=='string' and _ps:match({ascii_obfuscate('^function: 0x0000')}) then return false end "
        f"end "
        f"return true "
        f"end "
    )

    wrapper = (
        f"local {v_guard}=false "
        f"{init_and_check}"
        f"local function {v_fn}() "
        f"if {v_guard} then return end "
        f"{v_guard}=true "
        f"{v_init}() "
        f"if not {v_chk}() then return end "
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

    v_t = randomName()
    v_bx = randomName()
    v_ch = randomName()
    v_by = randomName()
    v_rp = randomName()
    v_tc = randomName()
    v_ti = randomName()
    v_fl = randomName()
    v_rn = randomName()
    v_rt = randomName()
    v_dt = randomName()

    protected_names = {v_t, v_bx, v_ch, v_by, v_rp, v_tc, v_ti, v_fl, v_rn, v_rt, v_dt}

    pool_tags = [generate_pool_tag() for _ in range(POOL_COUNT)]
    pool_list_lua = "{" + ",".join(lua_quote(t) for t in pool_tags) + "}"

    macro_processed = apply_moonveil_style_macros(sourceCode)
    minified_user_code = minify_payload(macro_processed)
    obfuscated_user_code = obfuscate_identifiers(minified_user_code, protected_names)
    obfuscated_user_code = obfuscate_strings_and_numbers(
        obfuscated_user_code, encrypt_strings=True, obfuscate_nums=True
    )

    bootstrap = build_bootstrap_helpers(v_t, v_bx, v_ch, v_by, v_rp, v_tc, v_ti, v_fl, v_rn, v_rt, v_dt)
    at_core = minify_payload(build_anti_tamper_core(pool_list_lua))
    extra_prots = minify_payload(getExtraProtections(pool_tags))
    filler_22k = "".join(build22kBlock(pool_tags, v_t, v_rt) for _ in range(max(1, repeat_22k)))

    reg_statements = [
        f"if {v_t}({v_rt})=='table'then {v_rt}[{lua_quote(tag)}]=true end if type(_G)=='table'then _G[{lua_quote(tag)}]=true end"
        for tag in pool_tags
    ]
    flattened_reg = flatten_control_flow(reg_statements, v_t)

    vm_prot = buildVMBlock(extra_prots + " " + at_core, pool_tags, v_t, v_ch, v_tc, v_ti, v_rt)
    vm_user = buildVMBlock(obfuscated_user_code, pool_tags, v_t, v_ch, v_tc, v_ti, v_rt)

    mc_var = randomName()
    final_code = (
        f"{bootstrap}"
        f"local {mc_var}={{}}for _i=1,360 do {mc_var}[_i]={v_rp}('X',24)end {mc_var}=nil "
        f"if {v_t}(collectgarbage)=='function'then if {v_t}(pcall)=='function'then pcall(collectgarbage)else collectgarbage()end end "
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
    ap.add_argument("input", nargs="?")
    ap.add_argument("-o", "--output", default="obfuscated.lua")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--repeat-22k", type=int, default=2)
    ap.add_argument("--heartbeat-demo", action="store_true")

    args, _ = ap.parse_known_args()

    try:
        if args.heartbeat_demo or not args.input:
            src = HEARTBEAT_TEMPLATE
        else:
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
