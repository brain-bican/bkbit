"""
This script provides a utility for trimming a LinkML schema by retaining specified classes, slots, and enums, along with their dependencies.

It defines a `YamlTrimmer` class for schema manipulation and offers a command-line interface using Click for easy usage from the terminal.

Usage:
    python script.py [OPTIONS] SCHEMA

Options:
    --classes, -c TEXT  Comma-separated list of classes to include in the trimmed schema (required).
    --slots, -s TEXT    Comma-separated list of slots to include in the trimmed schema.
    --enums, -e TEXT    Comma-separated list of enums to include in the trimmed schema.

Example:
    python script.py schema.yaml -c Person,Organization -s name,age -e StatusEnum

The script performs the following steps:
1. Loads the specified LinkML schema.
2. Trims the schema by keeping only the specified classes, slots, and enums, along with their dependencies.
3. Serializes and prints the trimmed schema in YAML format.

Dependencies:
    - click
    - linkml-runtime
    - linkml

"""

from dataclasses import dataclass
from typing import Union
from pathlib import Path
from linkml_runtime.linkml_model.meta import SchemaDefinition
from linkml_runtime.utils.schemaview import SchemaView
from linkml._version import __version__
from linkml.generators.yamlgen import YAMLGenerator
import click

@dataclass
class YamlTrimmer:
    """
    A utility class for trimming a LinkML schema by retaining specified classes, slots, and enums, along with their dependencies.

    This class helps in generating a simplified version of a LinkML schema by removing all elements that are not reachable from the specified classes, slots, and enums to keep.

    Args:
        schema (Union[str, Path, SchemaDefinition]): The LinkML schema to be trimmed. It can be a file path, URL, or a `SchemaDefinition` object.

    Attributes:
        schemaview (SchemaView): An object representing the loaded schema, used for manipulation and traversal.

    Methods:
        trim_model(keep_classes: list[str], keep_slots: list[str] = [], keep_enums: list[str] = []):
            Trims the schema by keeping only the specified classes, slots, and enums, and their dependencies.

        serialize():
            Serializes and prints the trimmed schema in YAML format.

    Example:
        >>> yt = YamlTrimmer('path/to/schema.yaml')
        >>> yt.trim_model(['Person', 'Organization'], keep_slots=['name'], keep_enums=['StatusEnum'])
        >>> yt.serialize()
    """
    def __init__(self, schema: Union[str, Path, SchemaDefinition]):
        self.schemaview = SchemaView(schema)

    def trim_model(
        self,
        keep_classes: list[str],
        keep_slots: list[str] = [],
        keep_enums: list[str] = [],
    ):
        """
        Trims the model by removing classes, slots, and enums that are not reachable from the specified keep_classes, keep_slots, and keep_enums.

        Args:
            keep_classes (list[str]): List of classes to keep.
            keep_slots (list[str], optional): List of slots to keep. Defaults to [].
            keep_enums (list[str], optional): List of enums to keep. Defaults to [].
        """
        sv = self.schemaview
        # vistited_classes, visited_enums, and visited slots keep track of the classes, enums, and slots that are reachable from the input class, slots, and enums we are interested in keeping
        visited_classes = set()
        visited_slots = set()
        visited_enums = set()

        # stack is a list of classes, enums, and slots that we will traverse to find all reachable classes, enums, and slots
        stack = []
        stack.extend(keep_classes)
        stack.extend(keep_slots)
        stack.extend(keep_enums)

        # all_classes, all_enums, and all_slots are the set of all classes, enums, and slots defined in the given schema
        all_classes = set(sv.all_classes(imports=False))
        all_enums = set(sv.all_enums(imports=False))
        all_slots = set(sv.all_slots(imports=False, attributes=False))

        while stack:
            curr_node = stack.pop()
            if (
                curr_node in visited_classes
                or curr_node in visited_enums
                or curr_node in visited_slots
            ):
                continue

            # if curr_node is a class
            if curr_node in all_classes:
                visited_classes.add(curr_node)
                # add parent classes to stack
                for inherited_class in sv.class_parents(curr_node, imports=False):
                    if (
                        inherited_class not in visited_classes
                        and inherited_class in all_classes
                    ):
                        stack.append(inherited_class)

                # iterate through attributes/slots and add respective range to stack if type is a class or enum
                for slot in sv.class_slots(
                    curr_node, imports=False, direct=True, attributes=True
                ):
                    if slot not in visited_slots and slot in all_slots:
                        stack.append(slot)

            elif curr_node in all_slots:
                visited_slots.add(curr_node)
                for slot_range in sv.slot_range_as_union(
                    sv.get_slot(curr_node, strict=True)
                ):
                    if (
                        slot_range in all_classes and slot_range not in visited_classes
                    ) or (slot_range in all_enums and slot_range not in visited_enums):
                        stack.append(slot_range)
                for parent_slot in sv.slot_parents(curr_node, imports=False):
                    if parent_slot not in visited_slots and parent_slot in all_slots:
                        stack.append(parent_slot)

            elif curr_node in all_enums:
                visited_enums.add(curr_node)
                # add parent classes to stack
                for parent_enum in sv.enum_parents(curr_node, imports=False):
                    if parent_enum not in visited_enums and parent_enum in all_enums:
                        stack.append(parent_enum)

            else:
                raise ValueError(
                    f"ERROR: {curr_node} not found in schema classes, slots, or enums"
                )

        for c in all_classes:
            if c not in visited_classes:
                sv.delete_class(c)
        for e in all_enums:
            if e not in visited_enums:
                sv.delete_enum(e)
        for s in all_slots:
            if s not in visited_slots:
                sv.delete_slot(s)

    def serialize(self, schema_id, schema_name, schema_title, schema_version):
        """
        Serializes the schema using YAMLGenerator and prints the serialized output.
        """
        if schema_id:
            self.schemaview.schema.id = schema_id
        if schema_name:
            self.schemaview.schema.name = schema_name
        if schema_title:
            self.schemaview.schema.title = schema_title
        if schema_version:
            self.schemaview.schema.version = schema_version
        else:
            self.schemaview.schema.version = self.schemaview.schema.name + "-" + self.schemaview.schema.version
        self.schemaview.schema.created_by = "BICAN_bkbit_linkml-trimmer"
        print(YAMLGenerator(self.schemaview.schema).serialize())


@click.command()
## ARGUMENTS ##
# Argument #1: Schema file
@click.argument("schema")

## OPTIONS ##
# Option #1: Classes
@click.option('--classes', '-c', required=True, help='Comma-separated list of classes to include in trimmed schema')
# Option #2: Slots
@click.option('--slots', '-s', help='Comma-separated list of slots to include in trimmed schema')
# Option #3: Enums
@click.option('--enums', '-e', help='Comma-separated list of enums to include in trimmed schema')
@click.option('--schema_id', '-i', help='Updated schema id for trimmed schema')
@click.option('--schema_name', '-n', help='Updated schema name for trimmed schema')
@click.option('--schema_title', '-t', help='Updated schema title for trimmed schema')
@click.option('--schema_version', '-v', help='Updated schema version for trimmed schema')


def linkml_trimmer(schema, classes, slots, enums, schema_id, schema_name, schema_title, schema_version):
    """
    Trim a LinkMl schema based on a list of classes, slots, and enums to keep.
    """
    classes = [c.strip() for c in classes.split(',')]
    slots = [s.strip() for s in slots.split(',')] if slots else []
    enums = [e.strip() for e in enums.split(',')] if enums else []

    yt = YamlTrimmer(schema)
    yt.trim_model(classes, slots, enums)
    yt.serialize(schema_id, schema_name, schema_title, schema_version)

if __name__ == "__main__":
    linkml_trimmer()
