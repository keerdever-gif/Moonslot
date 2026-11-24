import re
import random
import argparse

HEADER = '''--[[ This code is protected by moonslot 1.02.1 + moonveil-vm fusion
     If you want real obfuscation with state-machine VM: https://discord.gg/ZMnTeuTZ5
]]\n'''

ANCHOR_SYMBOLS = list("@#$%&*+-=!?~^<>|/\\:;")
_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"
OPCODE_VARS = ["dr", "mn", "et", "gh", "ty", "ui", "op", "vu", "bn", "jg", "ka", "yh"]
POOL_COUNT = 8

_GLOBAL_USED_NAMES = set(OPCODE_VARS)

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

# ───────────────────────── helpers básicos ─────────────────────────

def reset_name_registry(extra_protected=None):
    _GLOBAL_USED_NAMES.clear()
    _GLOBAL_USED_NAMES.update(OPCODE_VARS)
    _GLOBAL_USED_NAMES.update({
        "and", "break", "do", "else", "elseif", "end", "false", "for", "function",
        "if", "in", "local", "nil", "not", "or", "repeat", "return", "then", "true",
        "until", "while", "pcall", "type", "math", "string", "table", "bit32",
        "game", "task", "loadstring", "load", "getfenv", "getgenv", "setfenv", "debug",
        "ipairs", "pairs", "next", "tostring", "rawget", "rawset", "setmetatable",
        "getmetatable", "typeof", "coroutine", "buffer", "os", "Instance", "workspace",
        "clonefunction", "hookfunction", "collectgarbage", "gethui", "UDim2", "Color3",
        "_G", "Enum", "_bx", "_i", "_x", "_f", "_p", "_ok", "_gv", "_okG", "_gvG",
        "_okS", "_okI", "_okC", "_okCl", "_okV", "_gvV", "_ps", "_hk"
    })
    if extra_protected:
        _GLOBAL_USED_NAMES.update(extra_protected)

def randomName(used_names=None) -> str:
    while True:
        cand = (
            "_"
            + random.choice("abcdefghijklmnopqrstuvwxyz")
            + "".join(random.choice(_BASE36) for _ in range(random.randint(3, 5)))
            + str(random.randint(100, 9999))
        )
        if cand in _GLOBAL_USED_NAMES:
            continue
        if used_names is not None and cand in used_names:
            continue
        _GLOBAL_USED_NAMES.add(cand)
        if used_names is not None:
            used_names.add(cand)
        return cand

def _str_from_bytes(s: str) -> str:
    raw = s.encode("utf-8")
    if not raw:
        return "''"
    nums = ",".join(str(b) for b in raw)
    return f"string.char({nums})"

def ascii_obfuscate(s: str) -> str:
    raw = s.encode("utf-8")
    if not raw:
        return "''"
    parts = []
    for b in raw:
        mode = random.randint(0, 3)
        if mode == 0:
            d = random.randint(1, 35)
            parts.append(f"({b + d}-{d})")
        elif mode == 1 and b >= 4:
            k = random.randint(2, 4)
            rem = b % k
            q = b // k
            parts.append(f"({q}*{k}+{rem})" if rem else f"({q}*{k})")
        elif mode == 2:
            x = random.randint(1, 90)
            parts.append(f"(_bx({b ^ x},{x}))")
        else:
            d1 = random.randint(1, 15)
            d2 = random.randint(1, 15)
            parts.append(f"({b + d1 + d2}-{d1}-{d2})")
    return f"string.char({','.join(parts)})"

def fragmented_ascii_obfuscate(s: str) -> str:
    raw = s.encode("utf-8")
    if not raw:
        return "''"
    c_fn = randomName()
    cat_fn = randomName()
    chunks = []
    for b in raw:
        mode = random.randint(0, 3)
        if mode == 0:
            d = random.randint(1, 35)
            expr = f"({b + d}-{d})"
        elif mode == 1 and b >= 4:
            k = random.randint(2, 4)
            rem = b % k
            q = b // k
            expr = f"({q}*{k}+{rem})" if rem else f"({q}*{k})"
        elif mode == 2:
            x = random.randint(1, 90)
            expr = f"(_bx({b ^ x},{x}))"
        else:
            d1 = random.randint(1, 15)
            d2 = random.randint(1, 15)
            expr = f"({b + d1 + d2}-{d1}-{d2})"
        chunks.append(f"{c_fn}({expr})")
    return (
        f"(function() local {c_fn}=(type(string)=='table'and type(string.char)=='function')and string.char or function()return ''end "
        f"local {cat_fn}=(type(table)=='table'and type(table.concat)=='function')and table.concat or function(t)local o=''for _,v in ipairs(t)do o=o..tostring(v or '')end return o end "
        f"return {cat_fn}({{{','.join(chunks)}}}) end)()"
    )

def generate_pool_tag() -> str:
    suffix = "".join(random.choice(ANCHOR_SYMBOLS) for _ in range(6))
    return f"[pool.a.d.d.{suffix}]"

def lua_quote(s: str) -> str:
    escaped = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
    )
    return f'"{escaped}"'

def _decode_lua_string_literal(val: str):
    if len(val) < 2 or val[0] not in ('"', "'") or val[-1] != val[0]:
        return None
    body = val[1:-1]
    out_chars = []
    i = 0
    n = len(body)
    escape_map = {
        "a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r",
        "t": "\t", "v": "\v", "\\": "\\", '"': '"', "'": "'"
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
        if b2 else ""
    )
    return (
        f"(function() local function {fn_name}()"
        f"local {c_fn}=(type(string)=='table'and type(string.char)=='function')and string.char or function()return ''end "
        f"local {x_fn}=(type(bit32)=='table'and type(bit32.bxor)=='function')and bit32.bxor or function(a,b)"
        f"if type(a)~='number'or type(b)~='number'then return 0 end "
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

def generate_opaque_predicate() -> str:
    r = random.randint(1, 99)
    return f"(_bx({r},{r})==0)"

# ───────────────────────── macros MoonVeil-style ─────────────────────────

def _extract_balanced_call(code: str, macro_name: str):
    pattern = re.compile(rf"\b{macro_name}\s*\(")
    matches = []
    pos = 0
    n = len(code)
    while pos < n:
        m = pattern.search(code, pos)
        if not m:
            break
        start = m.start()
        i = m.end() - 1
        depth = 0
        in_str = None
        escape = False
        found_end = -1
        while i < n:
            ch = code[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == in_str:
                    in_str = None
            else:
                if ch in ('"', "'"):
                    in_str = ch
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        found_end = i + 1
                        break
            i += 1
        if found_end != -1:
            matches.append((start, found_end, code[m.end():found_end - 1]))
            pos = found_end
        else:
            pos = m.end()
    return matches

def _replace_balanced_macro(code: str, macro_name: str, replacer_fn) -> str:
    spans = _extract_balanced_call(code, macro_name)
    if not spans:
        return code
    out = []
    last = 0
    for start, end, inner in spans:
        out.append(code[last:start])
        out.append(replacer_fn(inner, start))
        last = end
    out.append(code[last:])
    return "".join(out)

def _split_top_level_args(inner: str):
    args = []
    buf = []
    depth_p = depth_b = depth_c = 0
    in_str = None
    esc = False
    for ch in inner:
        if in_str:
            buf.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in ('"', "'"):
            in_str = ch
            buf.append(ch)
        elif ch == "(":
            depth_p += 1
            buf.append(ch)
        elif ch == ")":
            depth_p = max(0, depth_p - 1)
            buf.append(ch)
        elif ch == "[":
            depth_b += 1
            buf.append(ch)
        elif ch == "]":
            depth_b = max(0, depth_b - 1)
            buf.append(ch)
        elif ch == "{":
            depth_c += 1
            buf.append(ch)
        elif ch == "}":
            depth_c = max(0, depth_c - 1)
            buf.append(ch)
        elif ch == "," and depth_p == 0 and depth_b == 0 and depth_c == 0:
            args.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail or buf:
        args.append(tail)
    return args

def apply_moonveil_style_macros(code: str) -> str:
    for prefix in ("MS", "MV"):
        code = _replace_balanced_macro(code, f"{prefix}_OMIT", lambda _inner, _pos: "")
    code = re.sub(r"\b(?:MS|MV)_OMIT\b[^\n]*", "", code)

    for prefix in ("MS", "MV"):
        code = _replace_balanced_macro(code, f"{prefix}_CRASH", lambda _inner, _pos: "return")

        def _line_repl(_inner, pos):
            line_no = code[:pos].count("\n") + 1
            return obfuscate_number(line_no)

        code = _replace_balanced_macro(code, f"{prefix}_LINE", _line_repl)

        code = _replace_balanced_macro(
            code,
            f"{prefix}_OPAQUE",
            lambda inner, _pos: (
                f"({generate_opaque_predicate()} and ({inner.strip() or 'true'}))"
                if inner.strip() else generate_opaque_predicate()
            ),
        )
        code = _replace_balanced_macro(
            code,
            f"{prefix}_ASSUME",
            lambda inner, _pos: f"if not ({inner.strip()}) then return end" if inner.strip() else "",
        )
        code = _replace_balanced_macro(
            code,
            f"{prefix}_PRECHECK",
            lambda _inner, _pos: "if type(game)~='userdata' and type(game)~='table' then return end",
        )
        code = _replace_balanced_macro(
            code,
            f"{prefix}_REWRITE",
            lambda inner, _pos: f"(function() return ({inner.strip()}) end)()" if inner.strip() else "nil",
        )
        code = _replace_balanced_macro(
            code,
            f"{prefix}_ENC_FUNC",
            lambda inner, _pos: f"(function(...) return ({inner.strip()})(...) end)" if inner.strip() else "nil",
        )

        def _enc_str_repl(inner, _pos):
            raw_arg = inner.strip()
            dec = _decode_lua_string_literal(raw_arg)
            return encode_lua_string(dec) if dec is not None else raw_arg

        code = _replace_balanced_macro(code, f"{prefix}_ENC_STR", _enc_str_repl)

        def _vault_repl(inner, _pos):
            raw_arg = inner.strip()
            dec = _decode_lua_string_literal(raw_arg)
            return encode_lua_string(dec) if dec is not None else raw_arg

        code = _replace_balanced_macro(code, f"{prefix}_VAULT", _vault_repl)

        def _frag_repl(inner, _pos):
            raw_arg = inner.strip()
            dec = _decode_lua_string_literal(raw_arg)
            return fragmented_ascii_obfuscate(dec) if dec is not None else "''"

        code = _replace_balanced_macro(code, f"{prefix}_FRAG_STR", _frag_repl)

        code = _replace_balanced_macro(
            code,
            f"{prefix}_SHIELD",
            lambda inner, _pos: (
                f"(function() local {randomName()}={generate_opaque_predicate()} "
                f"return ({inner.strip()}) end)()"
                if inner.strip() else "nil"
            ),
        )
        code = _replace_balanced_macro(
            code,
            f"{prefix}_SELF_DESTRUCT",
            lambda inner, _pos: f"if not ({inner.strip()}) then return end" if inner.strip() else "",
        )
        code = _replace_balanced_macro(
            code,
            f"{prefix}_CHECK",
            lambda inner, _pos: f"if not ({inner.strip()}) then return end" if inner.strip() else "",
        )
        code = _replace_balanced_macro(
            code,
            f"{prefix}_SPLIT",
            lambda inner, _pos: f"((function() return ({inner.strip()}) end)())" if inner.strip() else "nil",
        )

        def _junk_repl(inner, _pos):
            s = inner.strip()
            cnt = int(s) if s.isdigit() else 1
            cnt = max(0, min(cnt, 50))
            return " ".join(f"local {randomName()}={random.randint(1, 9999)}" for _ in range(cnt))

        code = _replace_balanced_macro(code, f"{prefix}_JUNK", _junk_repl)
        code = _replace_balanced_macro(
            code,
            f"{prefix}_FAKE_BRANCH",
            lambda _inner, _pos: (
                f"if {generate_opaque_predicate()} then local {randomName()}={random.randint(1, 99)} end"
            ),
        )
        code = _replace_balanced_macro(
            code,
            f"{prefix}_NO_INLINE",
            lambda inner, _pos: (
                f"(function(...) local {randomName()}={inner.strip()} return {randomName()}(...) end)"
                if inner.strip() else "nil"
            ),
        )
        code = _replace_balanced_macro(
            code,
            f"{prefix}_WATERMARK",
            lambda _inner, _pos: lua_quote(randomName()),
        )

        def _idx_repl(inner, _pos):
            parts = _split_top_level_args(inner)
            if len(parts) < 2:
                return inner.strip()
            tbl_expr = parts[0]
            idx_expr = parts[1]
            if idx_expr.isdigit():
                idx_expr = obfuscate_number(int(idx_expr))
            return f"{tbl_expr}[{idx_expr}]"

        code = _replace_balanced_macro(code, f"{prefix}_INDEX_TO_NUM", _idx_repl)

        for passthrough in ("INLINE", "VM", "CFF", "COMPRESS", "OBFUSCATED"):
            code = _replace_balanced_macro(
                code,
                f"{prefix}_{passthrough}",
                lambda inner, _pos: inner.strip() if inner.strip() else "",
            )

    code = _replace_balanced_macro(code, "ATTRIBUTE", lambda _inner, _pos: "")
    return code

# ───────────────────────── bootstrap ─────────────────────────

def build_bootstrap_helpers(v_t, v_bx, v_ch, v_by, v_rp, v_tc, v_ti, v_fl, v_rn, v_rt, v_dt) -> str:
    return (
        f"local {v_t}=type "
        f"local {v_fl}=({v_t}(math)=='table'and {v_t}(math.floor)=='function')and math.floor or function(x)return x-(x%1)end "
        f"local {v_rn}=({v_t}(math)=='table'and {v_t}(math.random)=='function')and math.random or function(a)return a or 0 end "
        f"local {v_bx}=({v_t}(bit32)=='table'and {v_t}(bit32.bxor)=='function')and bit32.bxor or function(a,b)"
        f"if {v_t}(a)~='number' or {v_t}(b)~='number' then return 0 end "
        f"local r,p=0,1 while a>0 or b>0 do if(a%2)~=(b%2)then r=r+p end a={v_fl}(a/2)b={v_fl}(b/2)p=p*2 end return r end "
        f"local _bx={v_bx} "
        f"local {v_ch}=({v_t}(string)=='table'and {v_t}(string.char)=='function')and string.char or function()return''end "
        f"local {v_by}=({v_t}(string)=='table'and {v_t}(string.byte)=='function')and string.byte or function()return 0 end "
        f"local {v_rp}=({v_t}(string)=='table'and {v_t}(string.rep)=='function')and string.rep or function(s,n)local o=''for _=1,n do o=o..tostring(s or '')end return o end "
        f"local {v_tc}=({v_t}(table)=='table'and {v_t}(table.concat)=='function')and table.concat or function(t)local o=''if {v_t}(t)=='table'then for _,v in ipairs(t)do o=o..tostring(v or '')end end return o end "
        f"local {v_ti}=({v_t}(table)=='table'and {v_t}(table.insert)=='function')and table.insert or function(t,v)if {v_t}(t)=='table' then t[#t+1]=v end end "
        f"local {v_rt}=nil "
        f"if {v_t}(getgenv)=='function' then local _ok,_gv=pcall(getgenv) if _ok and {v_t}(_gv)=='table' then {v_rt}=_gv end end "
        f"if {v_t}({v_rt})~='table' then {v_rt}=_G end "
        f"local {v_dt}={{}} "
    )

# ───────────────────────── anti-tamper reforzado ─────────────────────────

def build_anti_tamper_core(pool_list_lua: str) -> str:
    f_flag = randomName()
    f_pools = randomName()
    f_root = randomName()
    f_safe = randomName()
    f_corrupt = randomName()
    f_has = randomName()
    chk_pools = randomName()
    chk_globals = randomName()
    chk_hooks_dbg = randomName()
    chk_meta_coro = randomName()
    chk_env_funs = randomName()
    chk_timing = randomName()
    chk_upvalues = randomName()
    chk_gc = randomName()
    chk_string_dump = randomName()
    chk_newproxy = randomName()
    chk_line_hook = randomName()

    s_hook_pat = fragmented_ascii_obfuscate("^function: 0x0000")
    s_info_mode = ascii_obfuscate("u")
    s_c_a = fragmented_ascii_obfuscate("cat")
    s_c_b = fragmented_ascii_obfuscate("dog")
    s_math_k = ascii_obfuscate("math")
    s_env_ok = fragmented_ascii_obfuscate("env_ok")
    s_env_k = ascii_obfuscate("env")
    s_val_k = ascii_obfuscate("val")
    s_junk = fragmented_ascii_obfuscate("x9z_corrupt")

    return f"""
local {f_flag} = false
local {f_pools} = {pool_list_lua}
local {f_root} = nil
if type(getgenv) == "function" then
    local _okG, _gvG = pcall(getgenv)
    if _okG and type(_gvG) == "table" then {f_root} = _gvG end
end
if type({f_root}) ~= "table" then {f_root} = _G end

local function {f_safe}(fn, ...)
    if type(fn) ~= "function" then return false, nil end
    if type(pcall) == "function" then return pcall(fn, ...) end
    return true, fn(...)
end

local function {f_corrupt}()
    {f_flag} = true
    if type({f_pools}) == "table" then
        for k in pairs({f_pools}) do {f_pools}[k] = {s_junk} end
        for _, key in ipairs({f_pools}) do
            if type(key) == "string" then
                if type({f_root}) == "table" then {f_root}[key] = nil end
                if type(_G) == "table" then _G[key] = nil end
            end
        end
    end
end

local function {f_has}(key)
    if type({f_root}) == "table" and {f_root}[key] == true then return true end
    if type(_G) == "table" and _G[key] == true then return true end
    return false
end

local function {chk_pools}()
    if {f_flag} then return end
    if type({f_pools}) ~= "table" or #{f_pools} < 8 then {f_corrupt}() return end
    for _, key in ipairs({f_pools}) do
        if not {f_has}(key) then {f_corrupt}() return end
    end
end

local function {chk_globals}()
    if {f_flag} then return end
    if type(type) ~= "function" or type(pcall) ~= "function" or type(tostring) ~= "function" then
        {f_corrupt}() return
    end
    if type(string) ~= "table" or type(string.char) ~= "function" or type(string.len) ~= "function" then
        {f_corrupt}() return
    end
    if type(table) ~= "table" or type(table.concat) ~= "function" or type(table.insert) ~= "function" then
        {f_corrupt}() return
    end
    if type(math) ~= "table" or type(math.floor) ~= "function" then
        {f_corrupt}() return
    end
    if math.floor(1.5) ~= 1 or string.len({s_c_a}) ~= 3 then {f_corrupt}() return end
end

local function {chk_hooks_dbg}()
    if {f_flag} then return end
    for _, fnRef in ipairs({{print, warn, error, loadstring, load}}) do
        if type(fnRef) == "function" and type(tostring) == "function" then
            local _okS, sVal = {f_safe}(tostring, fnRef)
            if _okS and type(sVal) == "string" and sVal:match({s_hook_pat}) then
                {f_corrupt}() return
            end
        end
    end
    if type(debug) == "table" and type(debug.gethook) == "function" then
        local ok, hk = {f_safe}(debug.gethook)
        if ok and hk ~= nil then {f_corrupt}() return end
    end
    if type(debug) == "table" and type(debug.getinfo) == "function" then
        local okI, info = {f_safe}(debug.getinfo, function() end, {s_info_mode})
        if not okI or type(info) ~= "table" or info.nups == nil then {f_corrupt}() end
    end
end

local function {chk_meta_coro}()
    if {f_flag} then return end
    if type(coroutine) == "table" and type(coroutine.create) == "function" and type(coroutine.resume) == "function" then
        local co = coroutine.create(function() coroutine.yield(10); coroutine.yield(20) end)
        local _, v1 = coroutine.resume(co)
        local _, v2 = coroutine.resume(co)
        if v1 ~= 10 or v2 ~= 20 then {f_corrupt}() return end
    end
    if type(setmetatable) == "function" and type(getmetatable) == "function" then
        local mt = setmetatable({{}}, {{__index = function(_, k) return tostring(k) .. "_ok" end}})
        if mt[{s_env_k}] ~= {s_env_ok} then {f_corrupt}() return end
        local lockedT = setmetatable({{}}, {{__metatable = {s_env_ok}}})
        if getmetatable(lockedT) ~= {s_env_ok} then {f_corrupt}() return end
        local rawT = setmetatable({{}}, {{__newindex = function() end}})
        if type(rawset) == "function" and type(rawget) == "function" then
            rawset(rawT, {s_val_k}, 42)
            if rawget(rawT, {s_val_k}) ~= 42 then {f_corrupt}() end
        end
    end
end

local function {chk_env_funs}()
    if {f_flag} then return end
    if type(string) == "table" and type(string.char) == "function" then
        local okChar, resChar = {f_safe}(string.char, nil)
        if okChar and resChar == "" then {f_corrupt}() return end
    end
    if type(debug) == "table" and type(debug.getconstants) == "function" and type(debug.setconstant) == "function" then
        local function probeFn() local a = {s_c_a} return a end
        local okC, c = {f_safe}(debug.getconstants, probeFn)
        local idx = nil
        if okC and type(c) == "table" then
            for i, v in pairs(c) do
                if v == {s_c_a} then idx = i break end
            end
        end
        if idx and idx > 0 then
            local st = {f_safe}(debug.setconstant, probeFn, idx, {s_c_b})
            if st and probeFn() == {s_c_b} then {f_corrupt}() return end
        end
    end
    if type(clonefunction) == "function" and type(hookfunction) == "function" then
        local function probeA() return 1 end
        local okCl, ca = {f_safe}(clonefunction, probeA)
        if okCl and type(ca) == "function" then
            local st = {f_safe}(hookfunction, probeA, function() return 2 end)
            if st and probeA() == 2 and ca() == 1 then {f_corrupt}() end
        end
    end
end

local function {chk_upvalues}()
    if {f_flag} then return end
    if type(debug) == "table" and type(debug.getupvalue) == "function" then
        local function probe()
            local x = 42
            return function() return x end
        end
        local f = probe()
        local ok, name, val = {f_safe}(debug.getupvalue, f, 1)
        if ok and (name == nil or val ~= 42) then {f_corrupt}() end
    end
end

local function {chk_gc}()
    if {f_flag} then return end
    if type(collectgarbage) == "function" then
        local ok, before = {f_safe}(collectgarbage, "count")
        if ok and type(before) == "number" then
            local x = {{}}
            for i = 1, 1000 do x[i] = i end
            {f_safe}(collectgarbage, "collect")
            local ok2, after = {f_safe}(collectgarbage, "count")
            if ok2 and type(after) == "number" and after < before then {f_corrupt}() end
        end
    end
end

local function {chk_string_dump}()
    if {f_flag} then return end
    if type(string) == "table" and type(string.dump) == "function" then
        local f = function() return "test" end
        local ok, dumped = {f_safe}(string.dump, f)
        if not ok or type(dumped) ~= "string" or #dumped < 10 then {f_corrupt}() end
    end
end

local function {chk_newproxy}()
    if {f_flag} then return end
    if type(newproxy) == "function" then
        local ok, p = {f_safe}(newproxy, false)
        if not ok or type(p) ~= "userdata" then {f_corrupt}() end
    end
end

local function {chk_line_hook}()
    if {f_flag} then return end
    if type(debug) == "table" and type(debug.sethook) == "function" and type(debug.gethook) == "function" then
        local f = function() return 1 end
        local ok1 = {f_safe}(debug.sethook, f, "", 0)
        if ok1 then
            local ok2, hook = {f_safe}(debug.gethook)
            if ok2 and hook ~= nil then {f_corrupt}() end
            {f_safe}(debug.sethook)
        end
    end
end

local function {chk_timing}()
    if {f_flag} then return end
    if type(getgenv) == "function" and type(os) == "table" and type(task) == "table" and type(math) == "table" then
        local c = os.clock; local w = task.wait; local m = math.sin
        if type(c) == "function" and type(w) == "function" and type(m) == "function" then
            local t1 = c(); w(0.15); local t2 = c()
            local f = t2 - t1
            if f >= 0.14 and f < 0.8 then
                local a = 0
                local t3 = c()
                for i = 1, 100000 do a = a + m(i * 0.05) end
                local t4 = c()
                local d = t4 - t3
                if d <= 0.0001 or (type({f_root}) == "table" and {f_root}[{s_math_k}] ~= nil and type({f_root}[{s_math_k}]) ~= "table") then
                    {f_corrupt}()
                end
            end
        end
    end
end

{chk_pools}()
{chk_globals}()
{chk_hooks_dbg}()
{chk_meta_coro}()
{chk_env_funs}()
{chk_upvalues}()
{chk_gc}()
{chk_string_dump}()
{chk_newproxy}()
{chk_line_hook}()
{chk_timing}()
if {f_flag} then return end
"""

# ───────────────────────── decodificador VM estatal MoonVeil ─────────────────────────

def build_moonveil_state_decoder(payload: str, v_t, v_ch, v_by, v_bx) -> str:
    key1 = bytes(random.randint(1, 255) for _ in range(random.randint(8, 24)))
    key2 = bytes(random.randint(1, 255) for _ in range(random.randint(8, 24)))
    raw = payload.encode("utf-8")
    enc1 = bytes(b ^ key1[i % len(key1)] for i, b in enumerate(raw))
    enc2 = bytes(b ^ key2[i % len(key2)] for i, b in enumerate(enc1))

    def to_lua_bin(b):
        out = []
        for x in b:
            if 32 <= x < 127 and x not in (34, 92):
                out.append(chr(x))
            else:
                out.append(f"\\{x:03d}")
        return '"' + "".join(out) + '"'

    data_lua = to_lua_bin(enc2)
    k1_lua = to_lua_bin(key1)
    k2_lua = to_lua_bin(key2)

    v_data = randomName()
    v_k1 = randomName()
    v_k2 = randomName()
    v_out = randomName()
    v_idx = randomName()
    v_end = randomName()
    v_off = randomName()
    v_state = randomName()
    v_pos = randomName()
    v_kp = randomName()
    v_b1 = randomName()
    v_b2 = randomName()
    v_b = randomName()
    v_ok = randomName()
    v_fn = randomName()
    v_ld = randomName()

    s_init = random.randint(1000, 9999)
    s_loop = random.randint(10000, 19999)
    s_body = random.randint(20000, 29999)
    s_done = random.randint(30000, 39999)
    s_fail = random.randint(40000, 49999)

    init_off = random.randint(50, 200)

    decoder = f"""
local {v_data} = {data_lua}
local {v_k1} = {k1_lua}
local {v_k2} = {k2_lua}
local {v_out} = ""
local {v_state} = {s_init}
local {v_off} = {init_off}
local {v_end} = #{v_data} + {v_off} - 1
local {v_idx} = {v_off}
repeat
    if {v_state} == {s_init} then
        {v_idx} = {v_off}
        {v_state} = {s_loop}
    elseif {v_state} == {s_loop} then
        if {v_idx} > {v_end} then {v_state} = {s_done} else {v_state} = {s_body} end
    elseif {v_state} == {s_body} then
        {v_pos} = {v_idx} - {v_off} + 1
        {v_kp} = (({v_pos} - 1) % #{v_k1}) + 1
        {v_b1} = {v_by}({v_data}, {v_pos})
        {v_b2} = {v_by}({v_k2}, (({v_pos} - 1) % #{v_k2}) + 1)
        {v_b} = {v_bx}({v_b1}, {v_b2})
        {v_b} = {v_bx}({v_b}, {v_by}({v_k1}, {v_kp}))
        {v_out} = {v_out} .. {v_ch}({v_b})
        {v_idx} = {v_idx} + 1
        {v_state} = {s_loop}
    elseif {v_state} == {s_done} then
        break
    else
        {v_state} = {s_fail}
        break
    end
until false

local {v_ld} = (type(loadstring) == "function" and loadstring) or (type(load) == "function" and load) or nil
if type({v_ld}) == "function" and type({v_out}) == "string" and #{v_out} > 0 then
    local {v_ok}, {v_fn} = pcall({v_ld}, {v_out})
    if {v_ok} and type({v_fn}) == "function" then
        pcall({v_fn})
    end
end
"""
    return decoder

# ───────────────────────── anti-dump + watermark ─────────────────────────

def build_anti_dump() -> str:
    f_ok = randomName()
    f_dump = randomName()
    return f"""
do
    local {f_ok} = true
    if type(string) == "table" and type(string.dump) == "function" then
        local {f_dump} = function() return 1 end
        local ok, res = pcall(string.dump, {f_dump})
        if not ok or type(res) ~= "string" or #res < 10 then {f_ok} = false end
    end
    if type(debug) == "table" and type(debug.getupvalue) == "function" then
        local function p() local z = 7 return function() return z end end
        local f = p()
        local ok2, n2, v2 = pcall(debug.getupvalue, f, 1)
        if not ok2 or n2 ~= "" and v2 ~= 7 then
            if type(v2) ~= "number" or v2 ~= 7 then {f_ok} = false end
        end
    end
    if not {f_ok} then return end
end
"""

def build_watermark() -> str:
    tag = randomName()
    val = randomName()
    return f"""
local {tag} = "{randomName()}{random.randint(100000,999999)}"
local {val} = {tag}:len() + {tag}:byte(1)
"""

# ───────────────────────── bloques auxiliares ─────────────────────────

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
        elif c in ('"', "'"):
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
            while j < n and (
                code[j].isdigit()
                or (code[j] == "." and not has_dot and j + 1 < n and code[j + 1].isdigit())
            ):
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

def obfuscate_identifiers(code: str, protected_names) -> str:
    keywords = {
        "and", "break", "do", "else", "elseif", "end", "false", "for", "function",
        "if", "in", "local", "nil", "not", "or", "repeat", "return", "then", "true",
        "until", "while", "pcall", "type", "math", "string", "table", "bit32",
        "game", "task", "loadstring", "load", "getfenv", "getgenv", "setfenv", "debug",
        "ipairs", "pairs", "next", "tostring", "rawget", "rawset", "setmetatable",
        "getmetatable", "typeof", "coroutine", "buffer", "os", "Instance", "workspace",
        "clonefunction", "hookfunction", "collectgarbage", "gethui", "UDim2", "Color3",
        "_G", "Enum", "_bx",
    }
    keywords.update(OPCODE_VARS)
    keywords.update(protected_names)

    tokens = _tokenize_lua(code)
    local_vars = set()
    used_names = set(keywords) | set(_GLOBAL_USED_NAMES)

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
            else:
                while j < len(tokens):
                    if tokens[j][0] == "ident":
                        vname = tokens[j][1]
                        if vname not in keywords and len(vname) > 1:
                            local_vars.add(vname)
                        j += 1
                        while j < len(tokens) and tokens[j][0] == "ws":
                            j += 1
                        if j < len(tokens) and tokens[j][0] == "sym" and tokens[j][1] == ",":
                            j += 1
                            while j < len(tokens) and tokens[j][0] == "ws":
                                j += 1
                            continue
                    break

    mapping = {v: randomName(used_names) for v in sorted(local_vars)}
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

def obfuscate_strings_and_numbers(code: str, encrypt_strings=True, obfuscate_nums=True) -> str:
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
                    out.append(fragmented_ascii_obfuscate(decoded))
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
    tokens = _tokenize_lua(code)
    meaningful = [(k, v) for (k, v) in tokens if k not in ("ws", "comment")]
    block_keywords = {
        "local", "function", "return", "then", "do", "else", "elseif", "end", "until", "in"
    }
    no_space_after = {".", ":", "(", "[", "{", ",", ";"}
    no_space_before = {".", ":", "(", ")", "[", "]", "{", "}", ",", ";"}

    out = []
    for idx, (kind, tok) in enumerate(meaningful):
        out.append(tok)
        if idx < len(meaningful) - 1:
            nxt_kind, nxt = meaningful[idx + 1]
            left_word = tok[-1].isalnum() or tok[-1] == "_"
            right_word = nxt[0].isalnum() or nxt[0] == "_"
            needs_space = (
                (left_word and right_word)
                or (tok in block_keywords and nxt not in no_space_before)
                or (kind == "str" and nxt_kind in ("ident", "num"))
                or (kind in ("ident", "num") and nxt_kind == "str")
            )
            if needs_space and tok not in no_space_after and nxt not in no_space_before:
                out.append(" ")
    return "".join(out).strip()

def flatten_control_flow(statements, v_t) -> str:
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
    s_mt = fragmented_ascii_obfuscate("locked")
    s_chk = ascii_obfuscate("a")
    checks = "\n".join(
        f'    if type(getgenv) == "function" then local _okG,_gvG = pcall(getgenv) if _okG and type(_gvG) == "table" and _gvG[{lua_quote(tag)}] ~= true and (type(_G) ~= "table" or _G[{lua_quote(tag)}] ~= true) then return end end'
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

def buildVMBlock(payloadStr, pool_tags, v_t, v_ch, v_tc, v_ti, v_rt) -> str:
    v_dr, v_mn, v_et, v_gh, v_ty, v_ui, v_op, v_vu, v_bn, v_jg, v_ka, v_yh = OPCODE_VARS
    if "(_bx(" in payloadStr:
        bx_prelude = (
            "local function _bx(a,b) "
            "if type(a)~='number' or type(b)~='number' then return 0 end "
            "if type(bit32)=='table' and type(bit32.bxor)=='function' then return bit32.bxor(a,b) end "
            "local r,p=0,1 while a>0 or b>0 do if(a%2)~=(b%2)then r=r+p end a=math.floor(a/2)b=math.floor(b/2)p=p*2 end return r end "
        )
        payloadStr = bx_prelude + payloadStr

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
        f"if {v_t}({op_map})=='table' then "
        f"{v_op},{v_vu}={op_map}[1],{op_map}[2] "
        f"if {v_op}=={v_ka}[{v_dr}] and {v_t}({v_vu})=='string' then "
        f"{v_ti}({v_ty},{v_vu}) {v_ui}={v_ui}+1 "
        f"elseif {v_op}=={v_ka}[{v_et}] then break end "
        f"end "
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
    depth_paren = depth_bracket = depth_brace = 0
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
        if depth_paren < 0 or depth_bracket < 0 or depth_brace < 0:
            raise ValueError(
                f"Negative delimiter depth: ()={depth_paren}, []={depth_bracket}, {{}}={depth_brace}"
            )
    if depth_paren != 0 or depth_bracket != 0 or depth_brace != 0:
        raise ValueError(
            f"Unbalanced delimiters: ()={depth_paren}, []={depth_bracket}, {{}}={depth_brace}"
        )

# ───────────────────────── wrapper final ─────────────────────────

def wrap_final_code(code: str, pool_tags) -> str:
    v_fn = randomName()
    v_runner = randomName()
    v_guard = randomName()
    v_init = randomName()
    v_chk = randomName()
    v_root_ref = randomName()
    v_gv_fn = randomName()
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

    resolve_root = (
        f"local {v_root_ref}=nil "
        f"local {v_gv_fn}=(type(getgenv)=='function' and getgenv) or (type(_G)=='table' and type(_G[{gv_key}])=='function' and _G[{gv_key}]) or nil "
        f"if type({v_gv_fn})=='function' then "
        f"local _okV,_gvV=pcall({v_gv_fn}) "
        f"if _okV and type(_gvV)=='table' then {v_root_ref}=_gvV end "
        f"end "
        f"if type({v_root_ref})~='table' then {v_root_ref}=(type(_G)=='table' and type(_G[{g_key}])=='table' and _G[{g_key}]) or _G end "
    )

    init_and_check = (
        f"local function {v_init}() "
        f"{resolve_root}"
        f"{pool_init}"
        f"end "
        f"local function {v_chk}() "
        f"{resolve_root}"
        f"{pool_checks}"
        f"if type(debug)=='table' and type(debug.gethook)=='function' then "
        f"local _ok,_hk=pcall(debug.gethook) "
        f"if _ok and _hk~=nil then return false end "
        f"end "
        f"if type(print)=='function' and type(tostring)=='function' then "
        f"local _okS,_ps=pcall(tostring,print) "
        f"if _okS and type(_ps)=='string' and _ps:match({ascii_obfuscate('^function: 0x0000')}) then return false end "
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
        f"local {v_runner}=function() if type({v_fn})=='function' then return {v_fn}() end end "
        f"if type({v_runner})=='function' then {v_runner}() end"
    )
    return minify_payload(wrapper)

# ───────────────────────── ORQUESTADOR ─────────────────────────

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

    protected_names = {v_t, v_bx, v_ch, v_by, v_rp, v_tc, v_ti, v_fl, v_rn, v_rt, v_dt, "_bx"}
    reset_name_registry(protected_names)

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
    anti_dump = minify_payload(build_anti_dump())
    watermark = minify_payload(build_watermark())
    filler_22k = "".join(build22kBlock(pool_tags, v_t, v_rt) for _ in range(max(1, repeat_22k)))

    reg_statements = [
        f"if {v_t}({v_rt})=='table'then {v_rt}[{lua_quote(tag)}]=true end if type(_G)=='table'then _G[{lua_quote(tag)}]=true end"
        for tag in pool_tags
    ]
    flattened_reg = flatten_control_flow(reg_statements, v_t)

    vm_prot = buildVMBlock(extra_prots + " " + at_core, pool_tags, v_t, v_ch, v_tc, v_ti, v_rt)
    vm_user = build_moonveil_state_decoder(obfuscated_user_code, v_t, v_ch, v_by, v_bx)

    mc_var = randomName()
    final_code = (
        f"{bootstrap}"
        f"local {mc_var}={{}}for _i=1,360 do {mc_var}[_i]={v_rp}('X',24)end {mc_var}=nil "
        f"if {v_t}(collectgarbage)=='function'then if {v_t}(pcall)=='function'then pcall(collectgarbage)else collectgarbage()end end "
        f"{watermark}"
        f"{anti_dump}"
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
