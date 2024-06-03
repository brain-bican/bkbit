#  Model Converters

## Spreadsheet converter: `schema2model`

This converter allows to create a yaml linkml model from set of spreadsheets.
It can use either tsv files or Google Sheet as an input.

### Usage

```bash
$ bkbit schema2model --help

Usage: bkbit schema2model [OPTIONS] [SPREADSHEETS]...

  This converter allows to create a yaml linkml model from set of
  spreadsheets. It can either use tsv files or Google Sheet as an input.

  The default behavior is to run the converter starting with TSV files,
  specifying their paths as arguments, for example, model_spreadsheets/*tsv.

  If `--gsheet` option is used, the converter starts from downloading
  spreadsheets  from Google Sheets.  The argument must be a YAML file that has
  `gsheet_id` and a list of `sheets`  with `gid` (a unique identifier for each
  individual sheet) and `name` (optionally)  that will be used as a name of
  the downloaded TSV file (if not available `gid` wil be used).

Options:
  -o, --output FILENAME           Path for the yaml output file.
  -t, --template PATH             Optional template yaml file with standard
                                  classes that will be added to the model.
  --gsheet / --no-gsheet          Using Google Sheet as a source. If True, the
                                  arguments MUST be a yaml file with gsheet_id
                                  and gid of all the sheets  [default: no-
                                  gsheet]
  --gsheet-download-dir PATH      Path used to download Google Sheets. If not
                                  specified a default directory will be
                                  created.
  --fix_tsv / --no-fix_tsv        Fixing known issues with tsv files from
                                  Google Sheets.  [default: fix_tsv]
  --fix_tsv_save / --no-fix_tsv_save
                                  Keeping the fixed files, relevant only if
                                  fix_tsv=True  [default: no-fix_tsv_save]
  --repair / --no-repair          Standard Linkml auto-repair schema
                                  [default: repair]
  --fix_bican_model / --no-fix_bican_model
                                  Automated repair specifically for the BICAN
                                  YAML model  [default: fix_bican_model]
  --help                          Show this message and exit.
```

### Example

- Starting from TSV files:

```bash
bkbit schema2model -o model.yaml source_model/spreadsheets/*.tsv
```

- Starting from Google Sheets
```bash
bkbit schema2model -o model.yaml  --gsheet --gsheet-download-dir source_model/spreadsheets  source_model/gsheet.yaml
```
