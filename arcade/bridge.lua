-- Super Tank bridge (2026-10-31). Runs inside MAME (-autoboot_script) and listens on 127.0.0.1:$ARCADE_PORT;
-- tankenv.py connects and sends one command per line. Replies are one line, except "pix" (header + bytes).
--   hello                      -> ok <game> <frame>
--   set <0|1> <field name>     button/joystick field on or off until changed ("P1 Up", "Coin 1", ...)
--   tap <frames> <field name>  on for N frames, then off
--   release                    everything off
--   peek <addr> <len>          -> mem <hex>          (main CPU program space)
--   ramlist                    -> ram <start>-<end>,...   (RAM regions of the main CPU)
--   pix                        -> pix <w> <h> <n>\n<n bytes, 32-bit pixels>
--   throttle <0|1>             full speed off/on
--   sync <0|1>                 lockstep: the emulator waits for "run" after each batch (for the AI player)
--   run <frames>               -> ran <frame>         (in sync mode: emulate N frames, then wait again)
--   save <name> / load <name>  state files in -state_directory
--   poke <addr> <val>          write one byte (main CPU program space)
--   freeze <addr> <val>        write it again every frame (a cheat); "freeze <addr> off" stops, "unfreeze" clears all
--   exit
-- Notes from the 2026-10-31 probes: the frame subscription must be kept in a global or it is garbage collected, and
-- emu.file("socket.host:port") makes MAME the listening side.
local m = manager.machine
local port = os.getenv("ARCADE_PORT") or "9100"
local sock = emu.file("", 7)
local err = sock:open("socket.127.0.0.1:" .. port)
if err then print("ARCADE socket error", err) end

local fields = {}
for _, p in pairs(m.ioport.ports) do for name, f in pairs(p.fields) do fields[name] = f end end
local cpu = m.devices[":maincpu"]
local mem = cpu.spaces["program"]
local scr = nil
for _, s in pairs(m.screens) do scr = s; break end

local frame, buf, taps, frozen = 0, "", {}, {}
local sync, budget = false, 0

local function reply(s) sock:write(s .. "\n") end

local function handle(line)
  local cmd, rest = line:match("^(%S+)%s*(.*)$")
  if not cmd then return end
  if cmd == "hello" then reply("ok " .. m.system.name .. " " .. frame)
  elseif cmd == "set" then
    local v, name = rest:match("^(%d)%s+(.+)$")
    local f = fields[name or ""]
    if f then f:set_value(tonumber(v)); reply("ok") else reply("err no field " .. tostring(name)) end
  elseif cmd == "tap" then
    local n, name = rest:match("^(%d+)%s+(.+)$")
    local f = fields[name or ""]
    if f then f:set_value(1); taps[#taps + 1] = {f, frame + tonumber(n)}; reply("ok") else reply("err no field " .. tostring(name)) end
  elseif cmd == "release" then
    for _, f in pairs(fields) do if f.type_class ~= "dipswitch" and f.type_class ~= "config" then f:set_value(0) end end
    taps = {}; reply("ok")
  elseif cmd == "peek" then
    local a, n = rest:match("^(%S+)%s+(%d+)$")
    a = tonumber(a); n = math.min(tonumber(n), 65536)
    local t = {}
    for x = a, a + n - 1 do t[#t + 1] = string.format("%02x", mem:read_u8(x)) end
    reply("mem " .. table.concat(t))
  elseif cmd == "poke" then
    local a, v = rest:match("^(%S+)%s+(%S+)$")
    mem:write_u8(tonumber(a), tonumber(v)); reply("ok")
  elseif cmd == "freeze" then
    local a, v = rest:match("^(%S+)%s+(%S+)$")
    if v == "off" then frozen[tonumber(a)] = nil else frozen[tonumber(a)] = tonumber(v) end
    reply("ok")
  elseif cmd == "unfreeze" then frozen = {}; reply("ok")
  elseif cmd == "ramlist" then
    local t = {}
    for _, e in pairs(mem.map.entries) do
      if e.read and e.read.handlertype == "ram" then t[#t + 1] = string.format("%x-%x", e.address_start, e.address_end) end
    end
    reply("ram " .. table.concat(t, ","))
  elseif cmd == "pix" then
    local s, w, h = scr:pixels()
    sock:write(string.format("pix %d %d %d\n", w, h, #s)); sock:write(s)
  elseif cmd == "throttle" then m.video.throttled = rest == "1"; reply("ok")
  elseif cmd == "sync" then sync = rest == "1"; budget = 0; reply("ok")
  elseif cmd == "run" then budget = tonumber(rest) or 1
  elseif cmd == "save" then m:save(rest); reply("ok")
  elseif cmd == "load" then m:load(rest); reply("ok")
  elseif cmd == "exit" then reply("ok"); m:exit()
  else reply("err unknown " .. cmd) end
end

local function poll()
  local d = sock:read(4096)
  if d and #d > 0 then
    buf = buf .. d
    while true do
      local line, tail = buf:match("^([^\n]*)\n(.*)$")
      if not line then break end
      buf = tail
      handle(line)
    end
  end
end

ARCADE_SUB = emu.add_machine_frame_notifier(function()
  frame = frame + 1
  for i = #taps, 1, -1 do if frame >= taps[i][2] then taps[i][1]:set_value(0); table.remove(taps, i) end end
  for a, v in pairs(frozen) do mem:write_u8(a, v) end
  poll()
  if sync then
    budget = budget - 1
    if budget <= 0 then
      if budget == 0 then reply("ran " .. frame) end
      budget = 0
      -- lockstep: keep serving commands until the next "run"
      while sync and budget == 0 do poll() end
    end
  end
end)
print("ARCADE ready " .. m.system.name .. " port " .. port)
