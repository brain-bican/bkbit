# Spreadsheets converter to model

It can be used to create a yaml linkml file from tsv files or google sheets.

## Usage 

```bash
$ bkbit schema2model --help

Usage: bkbit schema2model [OPTIONS] [TSV_FILES]...

Options:
  -o, --output FILENAME           output file
  -t, --template PATH             template file
  --gsheet-id TEXT                Google sheets ID. If this is specified then
                                  the arguments MUST be a file with list of
                                  gid
  --gsheet-download-dir PATH      Path used to download Google Sheets
  --fix_tsv / --no-fix_tsv        Auto-repair tsv files  [default: no-fix_tsv]
  --repair / --no-repair          Auto-repair schema  [default: repair]
  --fix_bican_model / --no-fix_bican_model
                                  Auto-repair specifically for bican yaml
                                  model  [default: no-fix_bican_model]
  --help                          Show this message and exit.
```