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


def prepare_keys(source, target):
    """Normalize text conventions old hactool rejects, without changing key bytes."""
    raw = source.read_bytes()
    try:
        text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    except UnicodeError:
        raise ImportError('prod.keys is not a supported text file (UTF-8 or UTF-16).') from None
    parsed, entries, locations = [], [], {}
    for number, line in enumerate(text.splitlines(), 1):
        line = re.split(r'[#;]', line, maxsplit=1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r'([A-Za-z0-9_]+)\s*[,=]\s*([0-9a-fA-F]+)', line)
        if not match:
            raise ImportError(f'prod.keys line {number} is not a key_name = hexadecimal_value entry. No key values are shown.')
        name, value = match[1].lower(), match[2].lower()
        if len(value) % 2:
            raise ImportError(f'prod.keys line {number} ({name}) has an odd number of hexadecimal characters.')
        parsed.append((number, name, value))
    supplied = {name: value for _, name, value in parsed}
    for number, name, value in parsed:
        # NCA decryption can use supplied master keys directly. Bad console-side
        # derivation sources must not prevent loading an otherwise usable keyset.
        source = re.fullmatch(r'(?:mariko_)?master_kek_source_([0-9a-f]{2})', name)
        direct = supplied.get('master_key_' + source[1], '') if source else ''
        if source and len(value) != 32 and len(direct) == 32 and int(direct, 16):
            print(f'NSP import: skipping unused malformed {name} on line {number}; '
                  'the corresponding derived master key is supplied.', file=sys.stderr)
            continue
        entries.append(f'{name} = {value}\n')
        locations.setdefault(value, []).append(f'line {number} ({name})')
    if not entries:
        raise ImportError('prod.keys contains no key entries.')
    target.write_text(''.join(entries), encoding='ascii')
    os.chmod(target, 0o600)
    return locations


def extractor_error(stdout, stderr, returncode, key_locations=None):
    """Translate known diagnostics without ever forwarding extractor output or keys."""
    text = (stdout + '\n' + stderr).lower()
    if any(word in text for word in ('unrecognized option', 'unknown option', 'invalid option')):
        return 'This hactool version does not support the required options. Update hactool.'
    invalid_key = re.search(r'key \(([^\r\n]*)\) must be (\d+) hex digits', text)
    if invalid_key:
        locations = (key_locations or {}).get(invalid_key[1], [])
        if locations:
            return (f'prod.keys {", ".join(locations[:4])}: hactool expected {invalid_key[2]} '
                    f'hexadecimal characters, but the entry has {len(invalid_key[1])}. No key values are shown.')
        return ('A key entry has an invalid length or contains non-hex characters. '
                'Use an unmodified prod.keys dump from your own console; do not paste its contents.')
    if 'already has a corresponding titlekey' in text:
        return 'hactool found duplicate title-key entries.'
    if 'invalid nca header' in text:
        return ('hactool could not decrypt an NCA header. Your prod.keys may lack the correct header_key, '
                'or the NSP may be damaged. Use keys dumped from your own console.')
    if 'unable to match rights id to titlekey' in text:
        return ('A required title key is missing. Put your own title.keys beside prod.keys; '
                'it must contain keys for the base game and update when their tickets cannot supply them.')
    if 'failed to read nca header' in text:
        return 'An NCA header could not be read. Check that the NSP download/dump is complete.'
    if 'error while loading shared libraries' in text:
        return 'hactool cannot load a required system library. Repair or reinstall the hactool package.'
    if any(word in text for word in ('failed to write', 'no space left on device', 'could not save file')):
        return 'hactool could not write extracted files. Check free disk space and folder permissions.'
    if 'unable to locate romfs in base nca' in text:
        return 'hactool could not read the base game RomFS. Check the base NSP and its title key.'
    if returncode:
        # Preserve useful error messages, but exclude all key/value lines and redact
        # long hex sequences (including hex dumps separated by spaces or colons).
        safe = []
        for line in stderr.splitlines():
            if re.search(r'key|value|secret|rights.?id', line, re.I):
                continue
            if not re.match(r'^\s*(?:error|failed|unable|invalid|could not|cannot|fatal|usage|hactool)\b', line, re.I):
                continue
            line = re.sub(r'\b(?:[0-9a-fA-F]{2}[\s:-]*){8,}', '[redacted]', line)
            line = ''.join(c for c in line if c.isprintable())[:240]
            safe.append(line)
            if len(safe) == 4:
                break
        detail = ' '.join(safe) or 'No safe error detail was available.'
        return f'hactool failed with exit code {returncode}. {detail}'
    return None


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
        key_locations = prepare_keys(keys, keydir / 'prod.keys')
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

        def run(*args, stage):
            # Capture rather than forward hactool output: even failure logs must not contain keys.
            result = subprocess.run([executable, '--suppresskeys', '-k', str(keydir / 'prod.keys'), *map(str, args)],
                                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    errors='replace')
            reason = extractor_error(result.stdout, result.stderr, result.returncode, key_locations)
            if reason:
                raise ImportError(f'{stage}: {reason}')
            return result.stdout

        def program(directory, expected):
            found = []
            for path in sorted(directory.iterdir()):
                if path.suffix.lower() != '.nca':
                    continue
                info = run('-i', path, stage='Reading base NSP' if expected == BASE_ID else 'Reading update NSP')
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
            '--romfsdir', output / 'romfs', update_nca, stage='Merging base game and update')
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
