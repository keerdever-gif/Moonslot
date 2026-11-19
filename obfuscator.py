#!/usr/bin/env python3
# obfuscator.py — Luau VM obfuscator (Anti-Tamper 1x VM, User Script 18x VM)
import re
import random
import argparse

# ═══════════════════════════════════════════════════════════════════════════
# 1. WATERMARK Y ANTI-TAMPER
# ═══════════════════════════════════════════════════════════════════════════
HEADER = '''--[[
  Protected by Moonslot
  Unauthorized reproduction or distribution is prohibited.
]]'''

ANTI_TAMPER_CORE = r'''
local __at_fired = false
local __at_code, __at_text = nil, nil
local __R = {
    ["0x00"]="UNSPECIFIED_TAMPER", ["0x01"]="TIME_INTEGRITY_DRIFT_MISMATCH",
    ["0x02"]="HOOKFUNCTION_SANITY_HOOK_RETURN_MISMATCH", ["0x03"]="HOOKFUNCTION_SANITY_RESTORE_RETURN_MISMATCH",
    ["0x04"]="HOOKFUNCTION_SANITY_POINTER_MISMATCH", ["0x05"]="HOOKFUNCTION_SANITY_REHOOK_RETURN_MISMATCH",
    ["0x07"]="CRITICAL_FUNCTION_HOOKED_BOOT", ["0x09"]="CRITICAL_FUNCTION_HOOKED_RUNTIME",
    ["0x11"]="SERVER_TIME_OUT_OF_RANGE", ["0x12"]="TIME_INTEGRITY_MISSING_EPOCH_SOURCE",
    ["0x13"]="TIME_SOURCE_FROZEN", ["0x21"]="TRAP_PROXY_TOSTRING", ["0x24"]="TRAP_PROXY_LEN",
    ["0x26"]="TRAP_TABLE_TOSTRING", ["0x31"]="TRAP_TABLE_LEN", ["0x33"]="CRITICAL_FUNCTION_NON_NATIVE",
    ["0x34"]="THREAD_WAIT_ACCELERATED", ["0x36"]="THREAD_SPAWN_BLOCKED", ["0x38"]="THREAD_CHECK_NOT_STARTED",
    ["0x39"]="THREAD_DELAY_NOT_FIRED", ["0x40"]="THREAD_DELAY_TOO_EARLY", ["0x53"]="GLOBAL_METATABLE_CHANGED",
    ["0x54"]="REQUEST_FUNCTION_HOOKED", ["0x55"]="REQUEST_IS_LUA_CLOSURE", ["0x56"]="REQUEST_NOT_NATIVE_CLOSURE",
    ["0x68"]="WRITEFILE_BLOCKED", ["0x69"]="APPENDFILE_BLOCKED", ["0x6A"]="SETCLIPBOARD_BLOCKED",
    ["0x6B"]="TOCLIPBOARD_BLOCKED", ["0x6C"]="WRITE_CLIPBOARD_BLOCKED", ["0x6D"]="MAKEFOLDER_BLOCKED",
    ["0x6E"]="DELFOLDER_BLOCKED", ["0x6F"]="DELFILE_BLOCKED", ["0x70"]="SYN_WRITE_CLIPBOARD_BLOCKED",
    ["0x71"]="OTH_HOOK_FUNCTION_INVALID", ["0x72"]="OTH_UNHOOK_FUNCTION_INVALID",
    ["0x73"]="OTH_GET_ROOT_CALLBACK_INVALID", ["0x74"]="OTH_IS_HOOK_THREAD_INVALID",
    ["0x7A"]="CRITICAL_FUNCTION_OTH_HOOKED_BOOT", ["0x7B"]="CRITICAL_FUNCTION_OTH_HOOKED_RUNTIME",
}
local function __at_isNative(fn)
    if type(fn) ~= "function" then return false end
    if iscclosure then local ok,v=pcall(iscclosure,fn) if ok then return v==true end end
    if debug and debug.info then local ok,s=pcall(debug.info,fn,"s") if ok then return s=="[C]" end end
    if debug and debug.getinfo then local ok,i=pcall(debug.getinfo,fn,"S") if ok and type(i)=="table" then return i.what=="C" or i.source=="=[C]" end end
    return true
end
local function __at_isHooked(fn)
    if type(fn)~="function" then return false end
    if isfunctionhooked then local ok,v=pcall(isfunctionhooked,fn) if ok then return v==true end end
    return false
end
local function __at_checkEnv()
    if game==nil or type(game)=="table" then return "0x00" end
    if Instance==nil or type(Instance.new)~="function" then return "0x00" end
    local ok,players=pcall(function() return game:GetService("Players") end)
    if not ok or players==nil or typeof(players)~=typeof(game) then return "0x00" end
    return nil
end
local function __at_checkDebug()
    if not debug or type(debug.info)~="function" or type(debug.traceback)~="function" or type(string.match)~="function" then return "0x00" end
    local natives={debug.info,debug.traceback,pcall,string.match}
    for i=1,#natives do local ok,s=pcall(debug.info,natives[i],"s") if not ok or s~="[C]" then return "0x33" end end
    local ok,line=pcall(function() local function probe() return 1 end return debug.info(probe,"l") end)
    if not ok or type(line)~="number" then return "0x00" end
    local rawOk,rawErr=pcall(rawget)
    if rawOk or type(rawErr)~="string" then return "0x00" end
    if not string.match(rawErr,"^[^:]+:%d+:") then return "0x00" end
    if not (string.match(rawErr,"missing argument") or string.match(rawErr,"bad argument")) then return "0x00" end
    if string.match("rr6k3:231:jbkn7o","^[^:]+:(%d+):")~="231" then return "0x00" end
    if string.match("r9riq:-37:jbkn7o",".*:%s*(%-%d+):%s")~="-37" then return "0x00" end
    if string.match("n1os4:jbkn7o","^[^:]+:([a-z0-9]+)$")~="jbkn7o" then return "0x00" end
    if string.match("n1os4:jbkn7o","^__no_match__$")~=nil then return "0x00" end
    return nil
end
local function __at_checkHooks()
    if type(hookfunction)~="function" or type(restorefunction)~="function" then return nil end
    local function original(v) return v+1 end
    local function replacement(v) return v+2 end
    local before=original
    local okHook,hookRet=pcall(hookfunction,original,replacement)
    if not okHook then return "0x02" end
    if hookRet~=nil and type(hookRet)~="function" then return "0x02" end
    local okRestore,restoreRet=pcall(restorefunction,original)
    if not okRestore then return "0x03" end
    if restoreRet~=nil and type(restoreRet)~="function" then return "0x03" end
    if before~=original then return "0x04" end
    local okRehook,rehookRet=pcall(hookfunction,original,replacement)
    if not okRehook or (rehookRet~=nil and type(rehookRet)~="function") then pcall(restorefunction,original) return "0x05" end
    pcall(restorefunction,original)
    return nil
end
local function __at_checkCritical(runtime)
    local funcs={pcall,rawget,rawset,type,tostring,tonumber,setmetatable,getmetatable,
        string.byte,string.sub,string.match,string.char,table.concat,table.insert,math.floor,math.abs}
    for i=1,#funcs do
        local fn=funcs[i]
        if type(fn)=="function" then
            if __at_isHooked(fn) then return runtime and "0x09" or "0x07" end
            if not __at_isNative(fn) then return "0x33" end
        end
    end
    return nil
end
local __at_env=(getgenv and getgenv()) or _G
local __at_baseMeta=getmetatable and getmetatable(__at_env) or nil
local function __at_checkMeta()
    if getmetatable and getmetatable(((getgenv and getgenv()) or _G))~=__at_baseMeta then return "0x53" end
    return nil
end
local __at_request=__at_env.request or __at_env.http_request or (__at_env.syn and __at_env.syn.request)
local function __at_checkRequest()
    if type(__at_request)~="function" then return nil end
    if __at_isHooked(__at_request) then return "0x54" end
    if islclosure then local ok,v=pcall(islclosure,__at_request) if ok and v then return "0x55" end end
    if not __at_isNative(__at_request) then return "0x56" end
    return nil
end
local function __at_checkThreads()
    if type(task)~="table" then return nil end
    if type(task.wait)~="function" then return "0x38" end
    if type(task.spawn)~="function" then return "0x36" end
    if type(task.delay)~="function" then return "0x39" end
    local t1=os.clock() task.wait(0.1) local dt=os.clock()-t1
    if dt<0.05 then return "0x34" end
    if dt>1.0 then return "0x40" end
    local fired=false task.delay(0.05,function() fired=true end) task.wait(0.15)
    if not fired then return "0x39" end
    return nil
end
local function __at_canCall(fn,...)
    if type(fn)~="function" then return true end
    return pcall(fn,...)
end
local function __at_checkIo()
    if __at_env.writefile and not __at_canCall(__at_env.writefile,"syscure_probe_key","syscure_probe_message") then return "0x68" end
    if __at_env.appendfile and not __at_canCall(__at_env.appendfile,"syscure_probe_key","") then return "0x69" end
    if __at_env.setclipboard and not __at_canCall(__at_env.setclipboard,"syscure_probe_message") then return "0x6A" end
    if __at_env.toclipboard and not __at_canCall(__at_env.toclipboard,"syscure_probe_message") then return "0x6B" end
    if __at_env.write_clipboard and not __at_canCall(__at_env.write_clipboard,"syscure_probe_message") then return "0x6C" end
    if __at_env.makefolder and not __at_canCall(__at_env.makefolder,"syscure/cache") then return "0x6D" end
    if __at_env.delfolder and not __at_canCall(__at_env.delfolder,"syscure/cache") then return "0x6E" end
    if __at_env.delfile and not __at_canCall(__at_env.delfile,"syscure_probe_key") then return "0x6F" end
    if __at_env.syn and __at_env.syn.write_clipboard and not __at_canCall(__at_env.syn.write_clipboard,"syscure_probe_message") then return "0x70" end
    return nil
end
local function __at_checkOth(runtime)
    local oth=__at_env.oth
    if type(oth)~="table" then return nil end
    if oth.hook~=nil and type(oth.hook)~="function" then return "0x71" end
    local unhook=oth.unhook or oth.un_hook
    if unhook~=nil and type(unhook)~="function" then return "0x72" end
    if oth.get_root_callback~=nil and type(oth.get_root_callback)~="function" then return "0x73" end
    if oth.is_hook_thread~=nil and type(oth.is_hook_thread)~="function" then return "0x74" end
    if type(oth.hook)=="function" and __at_isHooked(oth.hook) then return runtime and "0x7B" or "0x7A" end
    return nil
end
local __at_epoch=os.time()
local function __at_checkTime()
    if type(__at_epoch)~="number" or __at_epoch<=0 then return "0x12" end
    local s=os.time()
    if type(s)~="number" then return "0x12" end
    if s<1700000000 then return "0x11" end
    if s>2200000000 then return "0x11" end
    if math.abs(s-__at_epoch)>86400 then return "0x01" end
    return nil
end
local function __at_checkGameTime()
    local da=workspace.DistributedGameTime task.wait(0.15)
    local db=workspace.DistributedGameTime
    if type(da)~="number" or type(db)~="number" or db<=da then return "0x13" end
    return nil
end
local function __at_checkHeartbeat()
    local ok,rs=pcall(function() return game:GetService("RunService") end)
    if not ok or not rs then return nil end
    local hits=0
    local conn=rs.Heartbeat:Connect(function() hits=hits+1 end)
    task.wait(0.2) conn:Disconnect()
    if hits<=0 then return "0x13" end
    return nil
end
local function __at_checkTrapProxy()
    local fired=false
    local proxy=setmetatable({},{__tostring=function() fired=true return "trap" end,__len=function() fired=true return 0 end})
    pcall(function() return tostring(proxy) end)
    if not fired then return "0x21" end
    fired=false pcall(function() return #proxy end)
    if not fired then return "0x24" end
    return nil
end
local function __at_checkTrapTable()
    local t={1,2,3,4,5}
    if #t~=5 then return "0x31" end
    local ts=tostring(t)
    if type(ts)~="string" or ts:sub(1,6)~="table:" then return "0x26" end
    return nil
end
local function __at_checkDataStore()
    local ok,obj=pcall(Instance.new,"DataStoreIncrementOptions")
    if not ok or not obj then return nil end
    local result=pcall(function()
        local data={hi=true,num=42,str="test"}
        obj:SetMetadata(data)
        local got=obj:GetMetadata()
        if not got or got.hi~=data.hi or got.num~=data.num or got.str~=data.str then error("ds") end
        obj:Destroy()
    end)
    if not result then return "0x00" end
    return nil
end
local function __at_checkTween()
    local ok,ts=pcall(function() return game:GetService("TweenService") end)
    if not ok or not ts then return nil end
    local result=pcall(function()
        local frame=Instance.new("Frame") frame.Position=UDim2.new(0,0,0,0)
        local info=TweenInfo.new(0.05) local goal={Position=UDim2.fromScale(1,1)}
        local t0=os.clock() local tw=ts:Create(frame,info,goal) tw:Play() tw.Completed:Wait()
        if os.clock()-t0<0.03 then error("fast") end
        frame:Destroy()
    end)
    if not result then return "0x00" end
    return nil
end
local function __at_fixHooks()
    if not pcall or not rawget or not getgenv then return end
    local ok,env=pcall(getgenv)
    if not ok or type(env)~="table" then return end
    local restore=rawget(env,"restorefunction")
    if type(restore)~="function" then return end
    local funcs={string and string.byte,setmetatable,pcall,rawget,rawset,pairs,type,getfenv,setfenv}
    for i=1,#funcs do local fn=funcs[i] if fn then pcall(restore,fn) end end
end
local function __at_run()
    local checks={__at_checkEnv,__at_checkDebug,__at_checkHooks,
        function() return __at_checkCritical(false) end,
        __at_checkMeta,__at_checkRequest,__at_checkThreads,
        __at_checkIo,function() return __at_checkOth(false) end,
        __at_checkTime,__at_checkGameTime,__at_checkHeartbeat,
        __at_checkTrapProxy,__at_checkTrapTable,__at_checkDataStore,__at_checkTween}
    for i=1,#checks do
        local ok,code=pcall(checks[i])
        if not ok then return "0x00","CHECK_EXCEPTION" end
        if code then return code,__R[code] or "TAMPER" end
    end
    return nil,nil
end
pcall(__at_fixHooks)
__at_code,__at_text=__at_run()

if __at_code then
    if __at_fired then return end
    __at_fired=true
    pcall(function()
        local e=(getgenv and getgenv()) or _G
        if type(e)=="table" then
            e.__sc_crashed=true e.hookfunction=nil e.getrawmetatable=nil e.getnamecallmethod=nil
        end
    end)
    local __troll=[==[
  ⠛⠛⣿⣿⣿⣿⣿⡷⢶⣦⣶⣶⣤⣤⣤⣀
  ⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀
  ⠀⠀⠀⠉⠉⠉⠙⠻⣿⣿⠿⠿⠛⠛⠛⠻⣿⣿⣇
  ⠀⠀⢤⣀⣀⣀⠀⠀⢸⣷⡄⠀ ⣀⣤⣴⣿⣿⣿⣆
  ⠀⠀⠀⠀⠹⠏⠀⠀⠀⣿⣧⠀⠹⣿⣿⣿⣿⡿⣿
  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠛⠿⠇⢀⣼⣿⣿⠛⢯⡿⡟
  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠦⠴⢿⢿⣿⡿⠷⠀⣿
  ⠀⠀⠀⠀⠀⠀⠀⠙⣷⣶⣶⣤⣤⣤⣤⣤⣶⣦⠃
  ⠀⠀⠀⠀⠀⠀⠀⢐⣿⣾⣿⣿⣿⣿⣿⣿⣿⣿
  ⠀⠀⠀⠀⠀⠀⠀⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇
  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠻⢿⣿⣿⣿⣿⠟
  Anti-Tamper — get a better environmental logger.
  ]==]
    if type(print) == "function" then pcall(print, __troll) end
    while true do end
end
'''

# ═══════════════════════════════════════════════════════════════════════════
# 2. FORMAT LUA (Compresión inteligente sin romper Strings)
# ═══════════════════════════════════════════════════════════════════════════
def format_lua_output(code, max_line=120):
    out = []
    buf = []
    i = 0
    n = len(code)
    line_len = 0
    st = 'normal'
    lstr_close = None
    lcom_close = None

    def flush():
        nonlocal buf, line_len
        if buf:
            line = ''.join(buf).rstrip()
            if line: out.append(line)
            buf = []
            line_len = 0

    while i < n:
        c = code[i]

        if st == 'dq':
            buf.append(c); line_len += 1
            if c == '\\' and i + 1 < n:
                buf.append(code[i+1]); line_len += 1; i += 2; continue
            if c == '"': st = 'normal'
            i += 1; continue

        if st == 'sq':
            buf.append(c); line_len += 1
            if c == '\\' and i + 1 < n:
                buf.append(code[i+1]); line_len += 1; i += 2; continue
            if c == "'": st = 'normal'
            i += 1; continue

        if st == 'lstr':
            if code.startswith(lstr_close, i):
                buf.append(lstr_close); line_len += len(lstr_close)
                i += len(lstr_close); st = 'normal'; continue
            buf.append(c); line_len += 1
            if c == '\n': flush()
            i += 1; continue

        if st == 'lcom':
            if code.startswith(lcom_close, i):
                buf.append(lcom_close); line_len += len(lcom_close)
                i += len(lcom_close); st = 'normal'; continue
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
                tok = code[i:i+3+len(eq)]
                buf.append(tok); line_len += len(tok)
                i += len(tok); st = 'lcom'; continue
            buf.append('--'); line_len += 2; i += 2; st = 'com'; continue

        if c == '[':
            m = re.match(r'\[(=*)\[', code[i:])
            if m:
                eq = m.group(1); lstr_close = ']' + eq + ']'
                tok = code[i:i+2+len(eq)]
                buf.append(tok); line_len += len(tok)
                i += len(tok); st = 'lstr'; continue

        if c == '"': st = 'dq'; buf.append(c); line_len += 1; i += 1; continue
        if c == "'": st = 'sq'; buf.append(c); line_len += 1; i += 1; continue

        buf.append(c); line_len += 1

        if c == '\n':
            flush(); i += 1; continue

        if line_len >= max_line:
            if c in ';,}':
                flush(); i += 1; continue
            if c == ' ':
                flush(); i += 1; continue
            else:
                s = ''.join(buf)
                idx = -1
                for k in range(len(s)-1, -1, -1):
                    if s[k] in ' ,;':
                        idx = k
                        break
                if idx > 0 and idx > len(s) * 0.5:
                    out.append(s[:idx].rstrip())
                    buf = [s[idx:].lstrip()]
                    line_len = len(buf[0])
                    i += 1
                    continue
        i += 1

    flush()
    return '\n'.join(out)

# ═══════════════════════════════════════════════════════════════════════════
# 3. SEAK OBFUSCATOR CORE (Junk Code + VM Optimizada)
# ═══════════════════════════════════════════════════════════════════════════
_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"

def randomName() -> str:
    return "_" + "".join(random.choice(_BASE36) for _ in range(6)) + str(random.randint(0, 999))

def heavyMath(n) -> str:
    if random.random() < 0.8: return str(n)
    a, b, c, d = random.randint(500, 3499), random.randint(2, 51), random.randint(10, 809), random.randint(2, 21)
    return f"((((({n}+{a})*{b})/{b})-{a})+(({c}*{d})/{d})-{c})"

def generateSingleJunkLine() -> str:
    r = random.random()
    if r < 0.2: return f"local {randomName()}={heavyMath(random.randint(0, 998))} "
    elif r < 0.35: return f"local {randomName()}=string.char({heavyMath(random.randint(0, 254))}) "
    elif r < 0.5: return f"if not({heavyMath(1)}=={heavyMath(1)}) then local x=1 end "
    elif r < 0.7: return f'if type(nil)=="number" then while true do local {randomName()}=1 end end '
    elif r < 0.85: return f'do local {randomName()}={{}} {randomName()}["_"]=1 {randomName()}=nil end '
    else: return 'if type(math.pi)=="string" then while true do end end '

def generateJunk(lines: int = 100) -> str:
    return "".join(generateSingleJunkLine() for _ in range(lines))

def applyCFF(blocks) -> str:
    stateVar = randomName()
    lua = f"local {stateVar}=1 while true do "
    for i, block in enumerate(blocks):
        if i == 0: lua += f"if {stateVar}==1 then {block} {stateVar}=2 "
        else: lua += f"elseif {stateVar}=={i + 1} then {block} {stateVar}={i + 2} "
    lua += f"elseif {stateVar}=={len(blocks) + 1} then break end end "
    return lua

def runtimeString(s: str) -> str:
    return "string.char(" + ",".join(str(ord(c)) for c in s) + ")"

def buildTrueVM(payloadStr: str) -> str:
    STACK, KEY, ORDER, POOL = randomName(), randomName(), randomName(), randomName()
    seed = random.randint(50, 249)
    vmCore = f"local {POOL}={{}} local {STACK}={{}} local {KEY}={seed} "
    chunkSize = 30
    realChunks = [payloadStr[i:i + chunkSize] for i in range(0, len(payloadStr), chunkSize)]
    realOrder = []
    
    # 20% reduction: 1.2x multiplier instead of 1.5x
    totalChunks = int(len(realChunks) * 1.2) if len(realChunks) > 1 else 1
    if totalChunks < len(realChunks): totalChunks = len(realChunks)
    
    currentReal, globalIndex = 0, 0

    for i in range(1, totalChunks + 1):
        # No more "local _mem = ..." spam. Everything goes to the POOL table directly.
        if currentReal < len(realChunks) and (random.random() > 0.4 or (totalChunks - i) == (len(realChunks) - currentReal)):
            realOrder.append(i)
            chunk = realChunks[currentReal]
            encryptedBytes = []
            for j in range(len(chunk)):
                enc = ord(chunk[j]) ^ ((seed + globalIndex) & 0xFF)
                encryptedBytes.append(str(enc))
                globalIndex += 1
            vmCore += f"{POOL}[{i}]={{{','.join(encryptedBytes)}}} "
            currentReal += 1
        else:
            fakeBytes = [str(random.randint(0, 254)) for _ in range(random.randint(5, 15))]
            vmCore += f"{POOL}[{i}]={{{','.join(fakeBytes)}}} "

    vmCore += f"local {ORDER}={{{','.join(str(n) for n in realOrder)}}} "
    idxVar, byteVar = randomName(), randomName()
    vmCore += f"local _gIdx=0 for _, {idxVar} in ipairs({ORDER}) do for _, {byteVar} in ipairs({POOL}[{idxVar}]) do "
    vmCore += f"table.insert({STACK}, string.char(bit32.bxor({byteVar}, ({KEY} + _gIdx) % 256))) _gIdx=_gIdx+1 end end "
    vmCore += f"local _e = table.concat({STACK}) {STACK}=nil "
    
    ASSERT = f'getgenv()[{runtimeString("assert")}]'
    LOADSTRING = f'getgenv()[{runtimeString("loadstring")}]'
    
    vmCore += f"{ASSERT}({LOADSTRING}(_e))() "
    return vmCore

def buildSingleVM(innerCode: str, handlerCount: int) -> str:
    DISPATCH = randomName()
    out = f"local {DISPATCH}={{}} "
    realIdx = random.randint(0, handlerCount - 1)
    
    for i in range(handlerCount):
        if i == realIdx: out += f"{DISPATCH}[{i+1}]=function(lM) {generateJunk(3)} {innerCode} end "
        else: out += f"{DISPATCH}[{i+1}]=function(lM) {generateJunk(2)} return nil end "
        
    execBlocks = [f"{DISPATCH}[{i+1}]({{}})" for i in range(handlerCount)]
    out += applyCFF(execBlocks)
    return out

def build1xVM(payloadStr: str) -> str:
    """1 sola capa de VM (usada para el anti-tamper para mantenerlo comprimido)"""
    vm = buildTrueVM(payloadStr)
    vm = buildSingleVM(vm, random.randint(3, 4))
    return vm

def build18xVM(payloadStr: str) -> str:
    """18 capas de VM (usada para el script del usuario)"""
    vm = buildTrueVM(payloadStr)
    for _ in range(18): 
        vm = buildSingleVM(vm, random.randint(3, 4))
    return vm

def buildAntiEnvProtection():
    antiEnvCode = """local p=game.Players.LocalPlayer\nlocal o=p.CameraMinZoomDistance\npcall(function()\np.CameraMinZoomDistance=-5\nend)\nprint(p.CameraMinZoomDistance~=o and"detected"or"pass")"""
    fragSize = 4 + random.randint(0, 2)
    fragments = [antiEnvCode[i:i + fragSize] for i in range(0, len(antiEnvCode), fragSize)]
    tableName = randomName()
    fragmentLines = [f"{tableName}[#{tableName}+1] = string.char({','.join(str(ord(c)) for c in frag)})" for frag in fragments]
    initLine = f"local {tableName} = {{}}"
    reconstructLine = f"local _reco = table.concat({tableName}); assert(loadstring(_reco))();"
    return initLine, fragmentLines, reconstructLine

def getExtraProtections() -> str:
    antiDebuggers = "if getmetatable(_G)~=nil then while true do end end if type(print)~=\"function\" then while true do end end "
    rawTampers = [
        'if math.pi<3.14 or math.pi>3.15 then _err() end', 'if bit32 and bit32.bxor(10,5)~=15 then _err() end',
        'if type(tostring)~="function" then _err() end', 'if not string.match("chk","^c.*k$") then _err() end',
        'if type(coroutine.create)~="function" then _err() end', 'if type(table.concat)~="function" then _err() end',
        'local _tm1=tick() local _tm2=tick() if _tm2<_tm1 then _err() end', 'if math.abs(-10)~=10 then _err() end',
        'if gcinfo and gcinfo()<0 then _err() end', 'if type(next)~="function" then _err() end',
        'if string.len("a")~=1 then _err() end', 'if type(table.insert)~="function" then _err() end',
        'if string.byte("Z",1)~=90 then _err() end', 'if math.floor(-1/10)~=-1 then _err() end',
        'if (true and 1 or 2)~=1 then _err() end', 'if type(1)~="number" then _err() end', 'if type(pcall)~="function" then _err() end'
    ]
    codeVaultGuards = ""
    for t in rawTampers:
        fnName, errName = randomName(), randomName()
        patched = t.replace('_err()', f'{errName}("!")')
        codeVaultGuards += f"local {fnName}=function() local {errName}=error {patched} end {fnName}() "
    return antiDebuggers + codeVaultGuards

# ═══════════════════════════════════════════════════════════════════════════
# 4. ORQUESTADOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════
def obfuscate(sourceCode: str, seed: int = 0) -> str:
    if not sourceCode: return '--ERROR'
    random.seed(seed)

    # 1. Preparar bloque de protección (Anti-Tamper + Anti-Env + Anti-Debug)
    initLine, fragmentLines, reconstructLine = buildAntiEnvProtection()
    antiEnvLines = [initLine] + fragmentLines + [reconstructLine]
    antiEnvCode = "\n".join(antiEnvLines)
    
    antiDebug = "local _t=tick() for _=1,150000 do end if tick()-_t>5.0 then while true do end end "
    extraProts = getExtraProtections()
    
    protection_payload = (
        "local __run_at = function()\n"
        + ANTI_TAMPER_CORE.strip() + "\n"
        + "end\n"
        + "pcall(__run_at)\n"
        + antiEnvCode + "\n"
        + antiDebug + "\n"
        + extraProts
    )

    # 2. Ofuscar protección con 1 SOLA VM (Comprimido)
    final_protection = build1xVM(protection_payload)

    # 3. Ofuscar script del usuario con 18 CAPAS DE VM
    isLoadstringRegex = re.compile(r'loadstring\s*\(\s*game\s*:\s*HttpGet\s*\(\s*["\']([^"\']+)["\']\s*\)\s*\)\s*\(\s*\)', re.IGNORECASE)
    match = isLoadstringRegex.search(sourceCode)
    
    # ELIMINADA la función detectAndApplyMappings que rompía la sintaxis.
    # Ahora pasamos el código tal cual, la VM lo encriptará sin romper strings ni comentarios.
    payloadToProtect = match.group(1) if match else sourceCode
    
    final_user_script = build18xVM(payloadToProtect)

    # 4. Ensamblar output final
    final_code = (
        f"{HEADER}\n\n"
        f"{final_protection}\n"
        f"{final_user_script}"
    )
    return format_lua_output(final_code, max_line=120)

# ═══════════════════════════════════════════════════════════════════════════
# 5. CLI
# ═══════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--output', default='obfuscated.lua')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--min-size', type=int, default=23000)
    args = ap.parse_args()
    with open(args.input, encoding='utf-8') as f: src = f.read()
    out = obfuscate(src, seed=args.seed)
    with open(args.output, 'w', encoding='utf-8') as f: f.write(out)

if __name__ == '__main__':
    main()
