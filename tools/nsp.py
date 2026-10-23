"""Import a base NSP and update using the user's keys and an installed hactool.

No keys or game data are downloaded. PFS0 paths and extents are validated before
any content is written. Extraction happens in a private staging directory.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile


BASE_ID = '01007ef00011e000'
UPDATE_ID = '01007ef00011e800'


class ImportError(ValueError):
    pass


def unpack(package, destination):
    """Extract only NCA and ticket entries from a bounded, flat PFS0 archive."""
    destination.mkdir()
    with open(package, 'rb') as source:
        size = os.fstat(source.fileno()).st_size
        header = source.read(16)
        if len(header) != 16 or header[:4] != b'PFS0':
            raise ImportError('Not an NSP (PFS0) file. NSZ/XCI are not supported.')
        count, names_size, _ = struct.unpack_from('<III', header, 4)
        if count > 100000 or names_size > 16 * 1024 * 1024:
            raise ImportError('Invalid NSP file table.')
        data_start = 16 + count * 24 + names_size
        if data_start > size:
            raise ImportError('Truncated NSP file table.')
        entries = source.read(count * 24)
        names = source.read(names_size)
        seen, ranges, selected = set(), [], []
        for i in range(count):
            offset, length, name_offset, _ = struct.unpack_from('<QQII', entries, i * 24)
            end = names.find(b'\0', name_offset)
            if name_offset >= len(names) or end < 0:
                raise ImportError('Invalid NSP filename.')
            try:
                name = names[name_offset:end].decode('utf-8')
            except UnicodeError:
                raise ImportError('Invalid NSP filename.') from None
            if not name or name in ('.', '..') or any(c in name for c in '/\\:') or any(ord(c) < 32 for c in name):
                raise ImportError('Unsafe NSP filename.')
            if name.lower() in seen or offset > size - data_start or length > size - data_start - offset:
                raise ImportError('Duplicate or out-of-bounds NSP entry.')
            seen.add(name.lower())
            if length:
                ranges.append((offset, offset + length))
            if name.lower().endswith(('.nca', '.tik')):
                selected.append((name, data_start + offset, length))
        ranges.sort()
        if any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
            raise ImportError('Overlapping NSP entries.')
        for name, offset, length in selected:
            source.seek(offset)
            with open(destination / name, 'xb') as target:
                while length:
                    chunk = source.read(min(length, 4 * 1024 * 1024))
                    if not chunk:
                        raise ImportError('Truncated NSP entry.')
                    target.write(chunk)
                    length -= len(chunk)


def ticket_key(path):
    """Common tickets hold an encrypted title key; personalized tickets need title.keys."""
    with open(path, 'rb') as stream:
        data = stream.read(4096)
    if len(data) < 4:
        raise ImportError('Truncated NSP ticket.')
    # Switch tickets store this integer little-endian (RSA-2048/SHA-256: 04 00 01 00).
    signature = struct.unpack_from('<I', data)[0]
    body = {0x10000: 0x240, 0x10001: 0x140, 0x10002: 0x80,
            0x10003: 0x240, 0x10004: 0x140, 0x10005: 0x80}.get(signature)
    if body is None or len(data) < body + 0x170:
        raise ImportError('Invalid NSP ticket.')
    if data[body + 0x141] != 0:
        return None
    return data[body + 0x160:body + 0x170].hex(), data[body + 0x40:body + 0x50].hex()


def import_nsp(base, update, keys, output, tool=None):
    executable = shutil.which(tool or os.environ.get('SAVAGEWIND_HACTOOL', 'hactool'))
    if not executable:
        raise ImportError('Install hactool, or set SAVAGEWIND_HACTOOL to its executable.')
    keys = Path(keys).resolve(strict=True)
    output = Path(output).resolve(strict=True)
    if any(output.iterdir()):
        raise ImportError('NSP staging directory must be empty.')
    # Never touch ~/.switch or persist keys in the installed game directory.
    with tempfile.TemporaryDirectory(prefix='.private-', dir=output) as private:
        private = Path(private)
        keydir = private / '.switch'
        keydir.mkdir(mode=0o700)
        shutil.copyfile(keys, keydir / 'prod.keys')
        os.chmod(keydir / 'prod.keys', 0o600)
        base_dir, update_dir = private / 'base', private / 'update'
        unpack(base, base_dir)
        unpack(update, update_dir)
        titlekeys = {}
        sibling = keys.with_name('title.keys')
        if sibling.is_file():
            for line in sibling.read_text().splitlines():
                match = re.fullmatch(r'\s*([0-9a-fA-F]{32})\s*=\s*([0-9a-fA-F]{32})\s*(?:#.*)?', line)
                if match:
                    titlekeys[match[1].lower()] = match[2].lower()
        for directory in (base_dir, update_dir):
            for ticket in directory.iterdir():
                if ticket.suffix.lower() == '.tik':
                    pair = ticket_key(ticket)
                    if pair:
                        titlekeys[pair[0]] = pair[1]
        title_file = keydir / 'title.keys'
        title_file.write_text(''.join(f'{rid} = {key}\n' for rid, key in titlekeys.items()))
        os.chmod(title_file, 0o600)
        env = dict(os.environ, HOME=str(private), USERPROFILE=str(private))
        # PyInstaller prepends its own libraries for swgen; hactool needs its normal loader search path.
        if getattr(sys, 'frozen', False):
            if 'LD_LIBRARY_PATH_ORIG' in env:
                env['LD_LIBRARY_PATH'] = env['LD_LIBRARY_PATH_ORIG']
            else:
                env.pop('LD_LIBRARY_PATH', None)

        def run(*args):
            # Capture rather than forward hactool output: even failure logs must not contain keys.
            result = subprocess.run([executable, '--suppresskeys', '-k', str(keydir / 'prod.keys'), *map(str, args)],
                                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    errors='replace')
            if result.returncode:
                raise ImportError('hactool could not read the NSP content. Check prod.keys and title.keys.')
            return result.stdout

        def program(directory, expected):
            found = []
            for path in sorted(directory.iterdir()):
                if path.suffix.lower() != '.nca':
                    continue
                info = run('-i', path)
                if re.search(r'^Content Type:\s+Program\s*$', info, re.M):
                    title = re.search(r'^Title ID:\s+([0-9a-fA-F]{16})\s*$', info, re.M)
                    if title and title[1].lower() == expected:
                        found.append(path)
            if len(found) != 1:
                raise ImportError('Select the Breath of the Wild base NSP and its matching 1.8.2 update NSP.')
            return found[0]

        base_nca = program(base_dir, BASE_ID)
        update_nca = program(update_dir, UPDATE_ID)
        run('-x', '--basenca', base_nca, '--exefsdir', output / 'exefs',
            '--romfsdir', output / 'romfs', update_nca)
        if not (output / 'exefs/main').is_file() or not (output / 'exefs/main.npdm').is_file() or not (output / 'romfs').is_dir():
            raise ImportError('Could not decrypt and merge game files. Check your keys and update NSP.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--update', required=True)
    parser.add_argument('--keys', required=True)
    parser.add_argument('--output', required=True, help='Existing empty staging directory')
    args = parser.parse_args(argv)
    try:
        import_nsp(args.base, args.update, args.keys, args.output)
    except (ImportError, OSError) as error:
        # OSError may name a file, but never includes its contents.
        parser.exit(1, f'NSP import: {error}\n')


if __name__ == '__main__':
    main()
