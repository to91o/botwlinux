"""Synthetic NSP import tests: no game files or console keys required."""
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import nsp


def archive(entries):
    names, table, data = b'', b'', b''
    for name, content in entries:
        table += struct.pack('<QQII', len(data), len(content), len(names), 0)
        names += name.encode() + b'\0'
        data += content
    return b'PFS0' + struct.pack('<III', len(entries), len(names), 0) + table + names + data


def ticket():
    data = bytearray(0x140 + 0x180)
    data[:4] = bytes.fromhex('04000100')  # Switch RSA-2048/SHA-256 signature type
    data[0x180:0x190] = bytes.fromhex('12' * 16)
    data[0x2a0:0x2b0] = bytes.fromhex('34' * 16)
    return bytes(data)


class NSPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nsp test ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def unpack(self, content):
        package = self.root / 'input.nsp'
        package.write_bytes(content)
        nsp.unpack(package, self.root / 'unpacked')

    def test_extract_selected_entries_only(self):
        self.unpack(archive([('program.NCA', b'content'), ('ticket.tik', b'ticket'), ('other.xml', b'skip')]))
        self.assertEqual({p.name for p in (self.root / 'unpacked').iterdir()}, {'program.NCA', 'ticket.tik'})
        self.assertEqual((self.root / 'unpacked/program.NCA').read_bytes(), b'content')

    def test_reject_traversal(self):
        for name in ('../evil.nca', '/evil.nca', 'C:evil.nca', 'dir\\evil.nca'):
            with self.subTest(name=name):
                directory = self.root / 'unpacked'
                if directory.exists():
                    directory.rmdir()
                with self.assertRaises(nsp.ImportError):
                    self.unpack(archive([(name, b'data')]))
        self.assertFalse((self.root / 'evil.nca').exists())

    def test_reject_duplicate_names(self):
        with self.assertRaises(nsp.ImportError):
            self.unpack(archive([('a.nca', b'a'), ('A.NCA', b'b')]))

    def test_reject_truncated_data(self):
        with self.assertRaises(nsp.ImportError):
            self.unpack(archive([('a.nca', b'content')])[:-1])

    def test_reject_overlapping_entries(self):
        content = bytearray(archive([('a.nca', b'aaa'), ('b.nca', b'bbb')]))
        struct.pack_into('<Q', content, 16 + 24, 1)
        with self.assertRaises(nsp.ImportError):
            self.unpack(content)

    def test_reject_invalid_string_offset(self):
        content = bytearray(archive([('a.nca', b'a')]))
        struct.pack_into('<I', content, 16 + 16, 9999)
        with self.assertRaises(nsp.ImportError):
            self.unpack(content)

    def test_reject_non_nsp(self):
        with self.assertRaises(nsp.ImportError):
            self.unpack(b'not an NSP archive')

    def test_common_and_personalized_tickets(self):
        path = self.root / 'test.tik'
        path.write_bytes(ticket())
        self.assertEqual(nsp.ticket_key(path), ('34' * 16, '12' * 16))
        data = bytearray(ticket())
        data[0x140 + 0x141] = 1
        path.write_bytes(data)
        self.assertIsNone(nsp.ticket_key(path))
        path.write_bytes(b'short')
        with self.assertRaises(nsp.ImportError):
            nsp.ticket_key(path)

    def test_switch_ticket_signature_encodings(self):
        path = self.root / 'signature.tik'
        for encoding, body in [('00000100', 0x240), ('01000100', 0x140),
                               ('02000100', 0x80), ('03000100', 0x240),
                               ('04000100', 0x140), ('05000100', 0x80)]:
            with self.subTest(encoding=encoding):
                data = bytearray(body + 0x180)
                data[:4] = bytes.fromhex(encoding)
                data[body + 0x40:body + 0x50] = bytes.fromhex('12' * 16)
                data[body + 0x160:body + 0x170] = bytes.fromhex('34' * 16)
                path.write_bytes(data)
                self.assertEqual(nsp.ticket_key(path), ('34' * 16, '12' * 16))

    def setup_import(self):
        base, update, keys, output = (self.root / n for n in ('base.nsp', 'update.nsp', 'prod.keys', 'output'))
        base.write_bytes(archive([('program.nca', b'base'), ('common.tik', ticket())]))
        update.write_bytes(archive([('program.nca', b'update')]))
        keys.write_text('header_key = synthetic-test-value\n')
        output.mkdir()
        return base, update, keys, output

    def fake_run(self, argv, **kwargs):
        # A test double checks the hactool protocol; it does not test real decryption.
        keydir = Path(kwargs['env']['HOME']) / '.switch'
        self.assertNotEqual(kwargs['env']['HOME'], os.environ.get('HOME'))
        self.assertEqual((keydir / 'title.keys').read_text(), '34' * 16 + ' = ' + '12' * 16 + '\n')
        self.assertEqual((keydir / 'prod.keys').stat().st_mode & 0o777, 0o600)
        self.assertNotIn('12' * 16, ' '.join(argv))
        self.assertIn('--suppresskeys', argv)
        if '-i' in argv:
            title = nsp.BASE_ID if Path(argv[-1]).read_bytes() == b'base' else nsp.UPDATE_ID
            return type('Result', (), {'returncode': 0, 'stderr': '', 'stdout': f'Content Type: Program\nTitle ID: {title}\n'})()
        self.assertIn('--basenca', argv)
        self.assertEqual(Path(argv[argv.index('--basenca') + 1]).read_bytes(), b'base')
        for option in ('--exefsdir', '--romfsdir'):
            Path(argv[argv.index(option) + 1]).mkdir()
        exefs = Path(argv[argv.index('--exefsdir') + 1])
        (exefs / 'main').write_bytes(b'synthetic NSO')
        (exefs / 'main.npdm').touch()
        return type('Result', (), {'returncode': 0, 'stderr': '', 'stdout': ''})()

    def test_merge_protocol_and_private_cleanup(self):
        args = self.setup_import()
        with patch('nsp.shutil.which', return_value='/test/hactool'), patch('nsp.subprocess.run', side_effect=self.fake_run) as run:
            nsp.import_nsp(*args)
        self.assertEqual(run.call_count, 3)
        self.assertEqual({p.name for p in args[-1].iterdir()}, {'exefs', 'romfs'})
        self.assertEqual(args[0].read_bytes(), archive([('program.nca', b'base'), ('common.tik', ticket())]))

    def test_extractor_failure_does_not_leak_output_or_keep_keys(self):
        args = self.setup_import()
        result = type('Result', (), {'returncode': 1, 'stdout': 'secret-key-value', 'stderr': 'secret-key-value'})()
        with patch('nsp.shutil.which', return_value='/test/hactool'), patch('nsp.subprocess.run', return_value=result):
            with self.assertRaises(nsp.ImportError) as error:
                nsp.import_nsp(*args)
        self.assertNotIn('secret-key-value', str(error.exception))
        self.assertEqual(list(args[-1].iterdir()), [])

    def test_reject_wrong_game_before_extraction(self):
        args = self.setup_import()
        result = type('Result', (), {'returncode': 0, 'stderr': '', 'stdout': 'Content Type: Program\nTitle ID: 0000000000000000\n'})()
        with patch('nsp.shutil.which', return_value='/test/hactool'), patch('nsp.subprocess.run', return_value=result) as run:
            with self.assertRaises(nsp.ImportError):
                nsp.import_nsp(*args)
        self.assertTrue(all('-i' in call.args[0] for call in run.call_args_list))
        self.assertEqual(list(args[-1].iterdir()), [])

    def test_refuse_nonempty_staging(self):
        args = self.setup_import()
        (args[-1] / 'keep').write_text('existing')
        with patch('nsp.shutil.which', return_value='/test/hactool'):
            with self.assertRaises(nsp.ImportError):
                nsp.import_nsp(*args)
        self.assertEqual((args[-1] / 'keep').read_text(), 'existing')

    def test_safe_extractor_diagnostics(self):
        cases = [('Invalid NCA header! Are keys correct?', 1, 'header_key'),
                 ('Unable to match rights id to titlekey. Update title.keys?', 0, 'title.keys'),
                 ("unrecognized option '--suppresskeys'", 1, 'Update hactool'),
                 ('Failed to read NCA header!', 1, 'complete'),
                 ('error while loading shared libraries: example.so', 127, 'system library'),
                 ('No space left on device', 1, 'disk space'),
                 ('Unable to locate RomFS in base NCA!', 1, 'base NSP'),
                 ('Key (PRIVATE) must be 32 hex digits!', 1, 'invalid length'),
                 ('Rights ID PRIVATE already has a corresponding titlekey!', 1, 'duplicate'),
                 ('unknown failure', 9, 'exit code 9')]
        for diagnostic, code, expected in cases:
            with self.subTest(diagnostic=diagnostic):
                message = nsp.extractor_error('key = secret-value', diagnostic, code)
                self.assertIn(expected, message)
                self.assertNotIn('secret-value', message)
        self.assertIsNone(nsp.extractor_error('normal output', '', 0))

    def test_fallback_diagnostics_redact_keys(self):
        secret = '1234567890abcdef1234567890abcdef'
        message = nsp.extractor_error('', 'Failed to open /example/file!\n'
                                      f'Error: {secret}\n'
                                      f'Key (not-even-hex) must be valid\n'
                                      '[WARN]: key value should stay private', 1)
        self.assertIn('Failed to open /example/file!', message)
        self.assertIn('[redacted]', message)
        self.assertNotIn(secret, message)
        self.assertNotIn('not-even-hex', message)
        self.assertNotIn('stay private', message)


if __name__ == '__main__':
    unittest.main()
