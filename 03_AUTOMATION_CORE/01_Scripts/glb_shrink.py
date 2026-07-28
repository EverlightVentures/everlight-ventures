#!/usr/bin/env python3
"""glb_shrink -- shrink Tripo/Higgsfield GLB exports for a phone-first web game.

WHY
Measured on bld_townhall.glb (a raw Tripo export, 16,612,924 B):
    textures 13,401,074 B  (81%)   <- three images, one of them a 7.6 MB JPEG
    geometry  3,209,452 B  (19%)   98,689 triangles
So the file is not a mesh problem, it is a TEXTURE problem. Tripo bakes multi-K maps that look
identical to a 1K map once the model is 200 world units away behind fog. Resizing them is the
single highest-leverage change available, and it needs no npm (the phone's proot segfaults on
npm install, so gltf-transform/draco are not reachable here).

WHAT IT DOES
Rebuilds the binary chunk from scratch, copying every bufferView in order and recording new
offsets, replacing image bufferViews with re-encoded versions. Rebuilding wholesale rather than
patching in place is deliberate: shrinking one image shifts every subsequent offset, and a
half-patched offset table produces a file that still parses but renders as garbage.

WHAT IT DOES NOT DO
No mesh decimation. 98k triangles per building is heavy but it is 19% of the bytes, and naive
decimation without a proper library wrecks silhouettes. Draco/meshopt remain the real fix for
geometry when a machine with npm is available.
"""
import struct, json, sys, os, io

JSON_CHUNK = 0x4E4F534A
BIN_CHUNK  = 0x004E4942


def parse(path):
    d = open(path, 'rb').read()
    magic, ver, total = struct.unpack('<III', d[:12])
    if magic != 0x46546C67:
        raise ValueError('not a GLB: %s' % path)
    off, js, bn = 12, None, b''
    while off < len(d):
        ln, ty = struct.unpack('<II', d[off:off + 8])
        body = d[off + 8: off + 8 + ln]
        if ty == JSON_CHUNK: js = json.loads(body.decode('utf-8'))
        elif ty == BIN_CHUNK: bn = body
        off += 8 + ln
    return js, bn


def shrink_image(raw, mime, max_px, quality):
    """Return (bytes, mime). Falls back to the original on any failure -- a texture that will not
    re-encode is not worth failing the whole build over."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw)); im.load()
        w, h = im.size
        scale = min(1.0, float(max_px) / max(w, h))
        if scale < 1.0:
            im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
        has_alpha = im.mode in ('RGBA', 'LA') and im.getextrema()[-1][0] < 255
        out = io.BytesIO()
        if has_alpha:
            im.save(out, 'PNG', optimize=True)      # alpha must survive; PNG is the only safe target
            return out.getvalue(), 'image/png'
        im.convert('RGB').save(out, 'JPEG', quality=quality, optimize=True, progressive=False)
        return out.getvalue(), 'image/jpeg'
    except Exception as e:
        sys.stderr.write('  ! re-encode failed (%s), keeping original\n' % e)
        return raw, mime


def shrink(src, dst, max_px=1024, quality=82):
    g, bn = parse(src)
    views = g.get('bufferViews', [])
    img_view = {}                                   # bufferView index -> image index
    for i, im in enumerate(g.get('images', [])):
        if 'bufferView' in im: img_view[im['bufferView']] = i

    new_bin = bytearray()
    for vi, v in enumerate(views):
        o, L = v.get('byteOffset', 0), v.get('byteLength', 0)
        chunk = bytes(bn[o:o + L])
        if vi in img_view:
            ii = img_view[vi]
            mime = g['images'][ii].get('mimeType', 'image/png')
            chunk, newmime = shrink_image(chunk, mime, max_px, quality)
            g['images'][ii]['mimeType'] = newmime
            sys.stderr.write('  image[%d] %10d -> %9d B  %s\n' % (ii, L, len(chunk), newmime))
        while len(new_bin) % 4: new_bin.append(0)   # bufferViews must stay 4-byte aligned
        v['byteOffset'] = len(new_bin)
        v['byteLength'] = len(chunk)
        new_bin += chunk
    while len(new_bin) % 4: new_bin.append(0)

    if g.get('buffers'): g['buffers'][0]['byteLength'] = len(new_bin)
    js = json.dumps(g, separators=(',', ':')).encode('utf-8')
    while len(js) % 4: js += b' '                   # JSON chunk pads with SPACES, bin pads with \0

    total = 12 + 8 + len(js) + 8 + len(new_bin)
    with open(dst, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total))
        f.write(struct.pack('<II', len(js), JSON_CHUNK)); f.write(js)
        f.write(struct.pack('<II', len(new_bin), BIN_CHUNK)); f.write(bytes(new_bin))
    return os.path.getsize(src), os.path.getsize(dst)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    mx = 1024; q = 82
    for a in sys.argv[1:]:
        if a.startswith('--max='): mx = int(a.split('=')[1])
        if a.startswith('--q='):   q = int(a.split('=')[1])
    tb = ta = 0
    for p in args:
        out = p.replace('.glb', '.min.glb')
        sys.stderr.write('%s\n' % os.path.basename(p))
        a, b = shrink(p, out, mx, q)
        tb += a; ta += b
        sys.stderr.write('  %,d -> %,d B  (%.1fx smaller)\n'.replace('%,d', '%d') % (a, b, a / max(1.0, float(b))))
    if len(args) > 1:
        sys.stderr.write('TOTAL %d -> %d B (%.1fx)\n' % (tb, ta, tb / max(1.0, float(ta))))
