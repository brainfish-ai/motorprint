"""Minimal reader for split (multi-disk) zip64 archives (.z01 ... .zip) using only the stdlib."""
import os, struct, zlib


class SplitZip:
    def __init__(self, parts):
        self.parts = parts
        self.sizes = [os.path.getsize(p) for p in parts]
        self.cum = [0]
        for s in self.sizes[:-1]: self.cum.append(self.cum[-1] + s)
        last = open(parts[-1], 'rb').read()
        loc = last.rfind(b'PK\x06\x07')
        _, z64disk, z64off, _ = struct.unpack('<IIQI', last[loc:loc + 20])
        rec = self._read(z64disk, z64off, 56)
        (_, _, _, _, _, _, _, n_tot, cd_size, cd_off) = struct.unpack('<IQHHIIQQQQ', rec)
        cd_disk = struct.unpack('<I', rec[20:24])[0]
        cd = self._read(cd_disk, cd_off, cd_size)
        self.entries = []
        p = 0
        while p < len(cd) and cd[p:p + 4] == b'PK\x01\x02':
            (method, csize, usize, nlen, xlen, clen, disk, roff) = (
                struct.unpack('<H', cd[p + 10:p + 12])[0], *struct.unpack('<II', cd[p + 20:p + 28]),
                *struct.unpack('<HHH', cd[p + 28:p + 34]), struct.unpack('<H', cd[p + 34:p + 36])[0],
                struct.unpack('<I', cd[p + 42:p + 46])[0])
            name = cd[p + 46:p + 46 + nlen].decode('utf8', 'replace')
            extra = cd[p + 46 + nlen:p + 46 + nlen + xlen]
            q = 0
            while q + 4 <= len(extra):
                hid, hlen = struct.unpack('<HH', extra[q:q + 4])
                if hid == 1:
                    vals = extra[q + 4:q + 4 + hlen]; k = 0
                    if usize == 0xFFFFFFFF: usize = struct.unpack('<Q', vals[k:k + 8])[0]; k += 8
                    if csize == 0xFFFFFFFF: csize = struct.unpack('<Q', vals[k:k + 8])[0]; k += 8
                    if roff == 0xFFFFFFFF: roff = struct.unpack('<Q', vals[k:k + 8])[0]; k += 8
                    if disk == 0xFFFF: disk = struct.unpack('<I', vals[k:k + 4])[0]
                q += 4 + hlen
            self.entries.append((name, method, csize, usize, disk, roff))
            p += 46 + nlen + xlen + clen

    def _read(self, disk, off, n):
        pos = self.cum[disk] + off
        out = b''
        while n > 0:
            i = max(j for j in range(len(self.cum)) if self.cum[j] <= pos)
            with open(self.parts[i], 'rb') as f:
                f.seek(pos - self.cum[i]); chunk = f.read(min(n, self.sizes[i] - (pos - self.cum[i])))
            out += chunk; pos += len(chunk); n -= len(chunk)
        return out

    def read(self, entry):
        name, method, csize, usize, disk, roff = entry
        hdr = self._read(disk, roff, 30)
        nlen, xlen = struct.unpack('<HH', hdr[26:30])
        data = self._read(disk, roff + 30 + nlen + xlen, csize)
        return data if method == 0 else zlib.decompress(data, -15)
