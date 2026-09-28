VERSION = "1.0.0"

-- PyKids helpers for Python files:
--   * after a line ending in ":" (if / for / while / def ...), indent the next line
--   * after return / break / continue / pass, un-indent the next line

local config = import("micro/config")

function init()
    config.RegisterCommonOption("pykids", "enabled", true)
end

local function isPython(bp)
    return bp.Buf:FileType() == "python"
end

function onInsertNewline(bp)
    if not isPython(bp) then return true end
    local c = bp.Cursor
    if c.Y == 0 then return true end

    local prev = bp.Buf:Line(c.Y - 1)
    local code = prev:gsub("%s*#.*$", "")   -- ignore trailing comments

    if code:match(":%s*$") then
        bp:InsertTab()
    elseif code:match("^%s+return%f[%W]") or code:match("^%s+break%s*$")
        or code:match("^%s+continue%s*$") or code:match("^%s+pass%s*$") then
        bp:OutdentLine()
    end
    return true
end
