#!/usr/bin/env python3
"""Functional tests for the RemapFrames VapourSynth plugin.

Usage: python3 test/test_remapframes.py [path/to/libremapframes.so]

Without an argument the plugin is expected to be autoloaded (e.g. from the
installed wheel) or to be found in site-packages/vapoursynth/plugins.

Requires the vapoursynth Python module (R55 or newer).
"""
import glob
import os
import sys
import tempfile

import vapoursynth as vs

core = vs.core

FRAMES = 20


def load_plugin(args):
    if args:
        core.std.LoadPlugin(args[0])
        return
    if hasattr(core, "remap"):
        return
    # Wheel layout: site-packages/vapoursynth/plugins/<plugin>
    plugin_dir = os.path.join(os.path.dirname(vs.__file__), "plugins")
    for ext in ("*.so", "*.dll", "*.dylib"):
        for path in glob.glob(os.path.join(plugin_dir, "*remapframes" + ext)):
            core.std.LoadPlugin(path)
            return
    raise SystemExit("FAIL: remap plugin is neither autoloaded nor found in " + plugin_dir)


def tagged_clip(name, frames=FRAMES, **kwargs):
    """A clip whose frames carry their index and clip name as frame properties."""
    base = core.std.BlankClip(width=64, height=32, length=frames, format=vs.GRAY8, **kwargs)

    def tag(n, f):
        f = f.copy()
        f.props["Idx"] = n
        f.props["Src"] = name
        return f

    return core.std.ModifyFrame(base, base, tag)


def frame_ids(clip):
    out = []
    for n in range(clip.num_frames):
        f = clip.get_frame(n)
        out.append((f.props["Src"].decode() if isinstance(f.props["Src"], bytes) else f.props["Src"], f.props["Idx"]))
    return out


def indices(clip):
    return [idx for _, idx in frame_ids(clip)]


def check(cond, msg):
    if not cond:
        raise SystemExit("FAIL: " + msg)
    print("ok  ", msg)


def expect_error(fn, msg):
    try:
        fn()
    except vs.Error as e:
        check(True, "%s (%s)" % (msg, str(e).strip().splitlines()[-1]))
    else:
        raise SystemExit("FAIL: no error raised: " + msg)


def main():
    load_plugin(sys.argv[1:])
    check(hasattr(core, "remap"), "plugin loaded (namespace remap)")
    for name in ["RemapFrames", "Remf", "RemapFramesSimple", "Remfs", "ReplaceFramesSimple", "Rfs"]:
        check(hasattr(core.remap, name), "function %s is registered" % name)

    base = tagged_clip("base")
    src = tagged_clip("src")

    # --- RemapFrames -------------------------------------------------------
    identity = core.remap.RemapFrames(base)
    check(identity.num_frames == FRAMES and indices(identity) == list(range(FRAMES)),
          "RemapFrames without mappings is the identity")

    out = core.remap.Remf(base, mappings="[0 9] [0 4]")
    check(indices(out)[:10] == [0, 0, 1, 1, 2, 2, 3, 3, 4, 4] and indices(out)[10:] == list(range(10, FRAMES)),
          "RemapFrames [a b] [y z] duplicates frames evenly")

    out = core.remap.Remf(base, mappings="10 5")
    check(indices(out)[10] == 5 and indices(out)[9] == 9 and indices(out)[11] == 11,
          "RemapFrames a z replaces a single frame")

    out = core.remap.Remf(base, mappings="[15 19] 6")
    check(indices(out)[15:] == [6] * 5, "RemapFrames [a b] z replaces a range with one frame")

    out = core.remap.Remf(base, mappings="[12 14] [14 12]")
    check(indices(out)[12:15] == [14, 13, 12], "RemapFrames reversed output range")

    out = core.remap.Remf(base, mappings="[0 3] [10 17]")
    check(indices(out)[:4] == [10, 12, 14, 16], "RemapFrames [a b] [y z] drops frames evenly")

    out = core.remap.Remf(base, mappings="3 4\n3 5")
    check(indices(out)[3] == 5, "RemapFrames: the last mapping of a frame wins")

    out = core.remap.Remf(base, mappings="# only a comment\n 1 2 # trailing comment\n#3 4")
    check(indices(out)[1] == 2 and indices(out)[3] == 3, "RemapFrames ignores comments")

    out = core.remap.Remf(base, mappings="[0 2] 7", sourceclip=src)
    ids = frame_ids(out)
    check(ids[:3] == [("src", 7)] * 3 and ids[3] == ("base", 3),
          "RemapFrames takes remapped frames from sourceclip and the rest from baseclip")
    check(out.width == base.width and out.format.id == base.format.id, "RemapFrames keeps the clip format")

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "mappings.txt")
        with open(path, "w") as fh:
            fh.write("# comment line\n[0 1] 9\n5 6\n")
        out = core.remap.Remf(base, filename=path)
        check(indices(out)[:2] == [9, 9] and indices(out)[5] == 6, "RemapFrames reads mappings from a file")
        out = core.remap.Remf(base, filename=path, mappings="5 7")
        check(indices(out)[5] == 7 and indices(out)[0] == 9, "RemapFrames: mappings string overrides the file")
        expect_error(lambda: core.remap.Remf(base, filename=os.path.join(tmp, "missing.txt")),
                     "RemapFrames rejects a missing file")

    expect_error(lambda: core.remap.Remf(base, mappings="0 99"), "RemapFrames rejects out of range frames")
    expect_error(lambda: core.remap.Remf(base, mappings="0 -1"), "RemapFrames rejects negative frames")
    expect_error(lambda: core.remap.Remf(base, mappings="[5 2] 0"), "RemapFrames rejects a reversed input range")
    expect_error(lambda: core.remap.Remf(base, mappings="x y"), "RemapFrames rejects garbage")
    expect_error(lambda: core.remap.Remf(base, mappings="[0 1 2"), "RemapFrames rejects an unclosed range")
    expect_error(lambda: core.remap.Remf(base, mappings="0 99999999999999999999"), "RemapFrames rejects overflowing numbers")

    short = tagged_clip("short", frames=FRAMES - 1)
    expect_error(lambda: core.remap.Remf(base, sourceclip=short), "RemapFrames rejects clips of different length")
    expect_error(lambda: core.remap.Remf(base, sourceclip=short, mismatch=True),
                 "RemapFrames rejects clips of different length even with mismatch=True")

    wide = tagged_clip("wide")
    wide = core.std.AddBorders(wide, right=64)
    expect_error(lambda: core.remap.Remf(base, sourceclip=wide, mappings="0 1"),
                 "RemapFrames rejects different dimensions by default")
    out = core.remap.Remf(base, sourceclip=wide, mappings="0 1", mismatch=True)
    check(out.width == 0 and out.height == 0, "RemapFrames mismatch=True yields variable dimensions")
    f0, f1 = out.get_frame(0), out.get_frame(1)
    check(f0.width == 128 and f1.width == 64 and f0.props["Idx"] == 1 and f1.props["Idx"] == 1,
          "RemapFrames mismatch=True returns frames of both sizes")

    other_fmt = core.std.BlankClip(base, format=vs.GRAY16)
    expect_error(lambda: core.remap.Remf(base, sourceclip=other_fmt, mappings="0 1"),
                 "RemapFrames rejects different formats by default")
    out = core.remap.Remf(base, sourceclip=other_fmt, mappings="0 1", mismatch=True)
    check(out.format is None or out.format.color_family == vs.UNDEFINED,
          "RemapFrames mismatch=True yields a variable format")
    check(out.get_frame(0).format.id == vs.GRAY16 and out.get_frame(1).format.id == vs.GRAY8,
          "RemapFrames mismatch=True returns frames of both formats")

    other_fps = core.std.AssumeFPS(src, fpsnum=25, fpsden=1)
    expect_error(lambda: core.remap.Remf(base, sourceclip=other_fps, mappings="0 1"),
                 "RemapFrames rejects different frame rates by default")
    out = core.remap.Remf(base, sourceclip=other_fps, mappings="0 1", mismatch=True)
    check(out.fps.numerator == 0, "RemapFrames mismatch=True yields a variable frame rate")

    # --- RemapFramesSimple -------------------------------------------------
    out = core.remap.RemapFramesSimple(base, mappings="0 1 2 3 4")
    check(out.num_frames == 5 and indices(out) == [0, 1, 2, 3, 4], "RemapFramesSimple keeps the first five frames")

    out = core.remap.Remfs(base, mappings="19 19 19")
    check(out.num_frames == 3 and indices(out) == [19] * 3, "RemapFramesSimple duplicates a frame")

    out = core.remap.Remfs(base, mappings="5\n # a comment\n 3 1 # trailing\n")
    check(indices(out) == [5, 3, 1], "RemapFramesSimple handles newlines and comments")

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "frames.txt")
        with open(path, "w") as fh:
            fh.write("# comment\n2 4\n6\n")
        out = core.remap.Remfs(base, filename=path)
        check(indices(out) == [2, 4, 6], "RemapFramesSimple reads frames from a file")
        expect_error(lambda: core.remap.Remfs(base, filename=path, mappings="0"),
                     "RemapFramesSimple rejects filename and mappings together")
        empty = os.path.join(tmp, "empty.txt")
        with open(empty, "w") as fh:
            fh.write("# nothing here\n")
        expect_error(lambda: core.remap.Remfs(base, filename=empty), "RemapFramesSimple rejects a file without frames")

    expect_error(lambda: core.remap.Remfs(base), "RemapFramesSimple requires filename or mappings")
    expect_error(lambda: core.remap.Remfs(base, mappings="   "), "RemapFramesSimple rejects an empty mappings string")
    expect_error(lambda: core.remap.Remfs(base, mappings="0 20"), "RemapFramesSimple rejects out of range frames")
    expect_error(lambda: core.remap.Remfs(base, mappings="[0 1]"), "RemapFramesSimple rejects ranges")

    # --- ReplaceFramesSimple -----------------------------------------------
    out = core.remap.ReplaceFramesSimple(base, src, mappings="[10 12] 15")
    ids = frame_ids(out)
    check(out.num_frames == FRAMES and all(idx == n for n, (_, idx) in enumerate(ids)),
          "ReplaceFramesSimple keeps frame numbers")
    check([s for s, _ in ids] == ["src" if n in (10, 11, 12, 15) else "base" for n in range(FRAMES)],
          "ReplaceFramesSimple takes the listed frames from sourceclip")

    out = core.remap.Rfs(base, src)
    check(all(s == "base" for s, _ in frame_ids(out)), "ReplaceFramesSimple without mappings returns baseclip")

    out = core.remap.Rfs(base, src, mappings="# comment\n 1 # trailing\n [3 4]")
    check([s for s, _ in frame_ids(out)][:6] == ["base", "src", "base", "src", "src", "base"],
          "ReplaceFramesSimple handles comments and ranges")

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "replace.txt")
        with open(path, "w") as fh:
            fh.write("0\n[18 19]\n")
        out = core.remap.Rfs(base, src, filename=path, mappings="2")
        srcs = [s for s, _ in frame_ids(out)]
        check(srcs[0] == "src" and srcs[2] == "src" and srcs[18:] == ["src", "src"] and srcs[1] == "base",
              "ReplaceFramesSimple combines file and mappings string")

    expect_error(lambda: core.remap.Rfs(base, src, mappings="20"), "ReplaceFramesSimple rejects out of range frames")
    expect_error(lambda: core.remap.Rfs(base, src, mappings="[1 2] 3 x"), "ReplaceFramesSimple rejects garbage")
    expect_error(lambda: core.remap.Rfs(base, short, mappings="1"), "ReplaceFramesSimple rejects clips of different length")
    expect_error(lambda: core.remap.Rfs(base, wide, mappings="1"), "ReplaceFramesSimple rejects different dimensions by default")
    out = core.remap.Rfs(base, wide, mappings="1", mismatch=True)
    check(out.width == 0 and out.get_frame(1).width == 128 and out.get_frame(0).width == 64,
          "ReplaceFramesSimple mismatch=True returns frames of both sizes")

    # --- Threading: out of order and parallel requests ----------------------
    out = core.remap.Remf(base, sourceclip=src, mappings="[0 19] [19 0]")
    frames = [out.get_frame_async(n) for n in [7, 2, 19, 0, 11, 5]]
    check([f.result().props["Idx"] for f in frames] == [12, 17, 0, 19, 8, 14],
          "parallel out of order frame requests")

    print("all tests passed")


if __name__ == "__main__":
    main()
