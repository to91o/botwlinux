# Import game files from NSP

In a build containing this feature, open **Game Files**, choose **Import NSP
packages**, then select your **base game NSP**, **1.8.2 update NSP** and
**prod.keys**. Choose **Set up game files**. To use extracted files instead,
choose **Game files folder** as before.

Install SciresM's `hactool` separately and put its executable on PATH, or set
`SAVAGEWIND_HACTOOL` to its absolute path before launching Savage Wind. It must
support `--suppresskeys`, `--basenca`, `--exefsdir` and `--romfsdir`. The launcher
does not download an extractor, game files or keys. Existing upstream release
downloads do not contain this new importer; rebuild the launcher and frozen
`swgen` helper together.

Use your own console's keys. Common tickets in the NSPs supply encrypted title
keys automatically. For NSPs with missing or personalized tickets, put your
`title.keys` next to the chosen `prod.keys` (lines in `rights_id = title_key`
format). Personalized tickets themselves are not decrypted by this importer.

For compatibility with hactool 1.4.0, the importer makes a temporary UTF-8 copy
of `prod.keys`, accepting UTF-8/UTF-16 byte-order marks and stripping `#`/`;`
comments. Key bytes and your original file are unchanged. Invalid entries are
reported by line number and key name, without displaying the key value.

The importer selects the Breath of the Wild program NCAs by title ID, then
uses the base NCA to merge the update's RomFS. The launcher checks the resulting
main module's build ID against the supported 1.8.2 version before replacing its
installed game files. A different game's package or an unsupported update is
rejected. DLC, NSZ and XCI import are not supported.

Allow substantially more free space than folder setup: both NSPs' NCAs and the
merged extracted files coexist with the installed files and runtime data image
during setup. The inputs are never modified. Temporary extraction files and
temporary keys are removed on success, failure and normal launcher exit. A
system crash or forced kill can leave a `.nsp-import-*` directory in the data
folder; remove that directory while Savage Wind is closed.

Errors are recorded in `nsp-import.log` in the data folder. Extractor output is
captured privately; only classified or filtered diagnostics are copied to the
log, with key/value lines excluded and long hexadecimal sequences redacted.
The normal extracted-folder setup and its version checks remain available.

For command-line extraction only (the output folder must exist and be empty):

```sh
python tools/nsp.py --base /path/base.nsp --update /path/update.nsp \
  --keys /path/prod.keys --output /path/empty-staging
```

Then choose that staging folder in the launcher's existing folder setup flow.
The command-line tool removes its private NCA/key workspace on failure but may
leave partially extracted `exefs`/`romfs` files in your staging directory.
