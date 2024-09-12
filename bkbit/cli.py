import click
from bkbit.model_converters.sheets_converter import schema2model
from bkbit.data_translators.library_generation_translator import specimenportal2jsonld

@click.group()
def cli():
    """A CLI tool with multiple commands."""
    pass

# Add commands to the CLI group
cli.add_command(schema2model)
cli.add_command(specimenportal2jsonld)

if __name__ == '__main__':
    cli()
