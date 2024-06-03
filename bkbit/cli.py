import click
from bkbit.model_converters.sheets_converter import schema2model

@click.group()
def cli():
    """A CLI tool with multiple commands."""
    pass

# Add commands to the CLI group
cli.add_command(schema2model)

if __name__ == '__main__':
    cli()
