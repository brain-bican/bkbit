import click
from bkbit.model_converters.sheets_converter import schema2model
from bkbit.model_converters.yaml2sheet_converter import yaml2cvs

@click.group()
def cli():
    """A CLI tool with multiple commands."""
    pass

# Add commands to the CLI group
cli.add_command(schema2model)
cli.add_command(yaml2cvs)

if __name__ == '__main__':
    cli()
