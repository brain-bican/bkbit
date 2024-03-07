import os
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Union
from pathlib import Path
import click
import pydantic
from linkml_runtime.linkml_model.meta import ClassDefinitionName, SlotDefinition, SchemaDefinition
from linkml_runtime.utils.formatutils import camelcase, underscore
from linkml_runtime.utils.schemaview import SchemaView

from linkml._version import __version__
from linkml.utils.generator import Generator, shared_arguments
from linkml.generators.yamlgen import YAMLGenerator

@dataclass
class YamlTrimmer():
    def __init__(self, schema: Union[str, Path, SchemaDefinition]):
        self.schemaview = SchemaView(schema)


    def trim_model(self, keep_classes, keep_slots, keep_enums, strict=False):
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

        
        #print(stack)

        # all_classes, all_enums, and all_slots are the set of all classes, enums, and slots defined in the given schema
        all_classes = set(sv.all_classes(imports=False))
        all_enums = set(sv.all_enums(imports=False))
        all_slots = set(sv.all_slots(imports=False, attributes=False))
        #print(f'All Classes: {all_classes}\n')

        while stack:
            curr_node = stack.pop()
            #print(f'Current Node: {curr_node}\n')
            if curr_node in visited_classes or curr_node in visited_enums or curr_node in visited_slots:
                continue

            # if curr_node is a class 
            if curr_node in all_classes:
                visited_classes.add(curr_node)
                # add parent classes to stack
                #print(f'Class Parents: {sv.class_parents(curr_node, imports=False)}\n')
                for inherited_class in sv.class_parents(curr_node, imports=False):
                    if inherited_class not in visited_classes and inherited_class in all_classes:
                        stack.append(inherited_class)
                #print(f'stack 1 : {stack}\n')

                # iterate through attributes/slots and add respective range to stack if type is a class or enum
                #print(f'Class Slots: {sv.class_slots(curr_node, imports=False, direct=True, attributes=True)}\n')
                for slot in sv.class_slots(curr_node, imports=False, direct=True, attributes=True):
                    if slot not in visited_slots and slot in all_slots:
                        stack.append(slot)
                        # visited_slots.add(slot)
                        # for slot_range in sv.slot_range_as_union(sv.get_slot(slot, strict=True)):
                        #     if (slot_range in all_classes and slot_range not in visited_classes) or (slot_range in all_enums and slot_range not in visited_enums):
                        #         stack.append(slot_range)
                        # #print(f"Slot: {slot.name} \n Parent Slots: {sv.slot_parents(slot.name, imports=False)}")
                        # for parent_slot in sv.slot_parents(slot, imports=False):
                        #     if parent_slot not in visited_slots and parent_slot in all_slots:
                        #         stack.append(parent_slot)
                                                  
            elif curr_node in all_slots:
                visited_slots.add(curr_node)
                for slot_range in sv.slot_range_as_union(sv.get_slot(curr_node, strict=True)):
                    if (slot_range in all_classes and slot_range not in visited_classes) or (slot_range in all_enums and slot_range not in visited_enums):
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
                print(f"ERROR: {curr_node} not found in schema classes, slots, or enums")
                return
            #print(f'stack: {stack}\n')

        # print(f'Visited Classes: {visited_classes}\n')
        # print(f'Visited Enums: {visited_enums}\n')
        # print(f'Visited Slots: {visited_slots}\n')
        for c in all_classes:
            if c not in visited_classes:
                sv.delete_class(c)
        for e in all_enums:
            if e not in visited_enums:
                sv.delete_enum(e)
        for s in all_slots:
            if s not in visited_slots:
                sv.delete_slot(s)
        print(YAMLGenerator(self.schemaview.schema).serialize())
        #return(template.materialize_derived_schema())
        #return (visited_classes, visited_enums, visited_slots)

# @shared_arguments(ERDiagramGenerator)
# @click.option(
#     "--structural/--no-structural",
#     default=True,
#     help="If True, then only the tree_root and entities reachable from the root are drawn",
# )
# @click.option(
#     "--exclude-attributes/--no-exclude-attributes",
#     default=False,
#     help="If True, do not include attributes in entities",
# )
# @click.option(
#     "--follow-references/--no-follow-references",
#     default=False,
#     help="If True, follow references even if not inlined",
# )
# @click.option("--max-hops", default=None, type=click.INT, help="Maximum number of hops")
# @click.option("--classes", "-c", multiple=True, help="List of classes to serialize")
# @click.version_option(__version__, "-V", "--version")
# @click.command()
# def cli(yamlfile, classes: List[str], max_hops: Optional[int], follow_references: bool, **args):
#     """Generate a mermaid ER diagram from a schema.

#     By default, all entities traversable from the tree_root are included. If no tree_root is
#     present, then all entities are included.

#     To create an ER diagram for selected classes, use the --classes option.
#     """
#     gen = ERDiagramGenerator(
#         yamlfile,
#         **args,
#     )
#     if classes:
#         print(gen.serialize_classes(classes))
#     else:
#         print(gen.serialize())


if __name__ == "__main__":
    # cli()
    # gen = ERDiagramGenerator(
    #     'examples/PersonSchema/personinfo.yaml',
        
    # )
    biolink_yaml = YamlTrimmer('../biolink-model/biolink-model.yaml')
    biolink_keep_classes = ['gene', 'genome', 'named thing', 'thing with taxon', 'entity', 'organism taxon', 'material sample', 'activity', 'procedure']
    biolink_keep_slots = [] #! look into slot:version
    biolink_keep_enums = []
    biolink_yaml.trim_model(biolink_keep_classes, biolink_keep_slots, biolink_keep_enums)
    # kbmodel_gars_classes = ['gene annotation', 'genome annotation', 'genome assembly', 'checksum']
    #kbmodel_gars_classes = ['gene annotation']
    #gen.serialize_classes_remove(gars_classes, follow_references=follow_references, max_hops=max_hops)