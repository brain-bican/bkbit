from dataclasses import dataclass
from typing import Union
from pathlib import Path
from linkml_runtime.linkml_model.meta import SchemaDefinition
from linkml_runtime.utils.schemaview import SchemaView

from linkml._version import __version__
from linkml.generators.yamlgen import YAMLGenerator


@dataclass
class YamlTrimmer:
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

    def serialize(self):
        """
        Serializes the schema using YAMLGenerator and prints the serialized output.
        """
        print(YAMLGenerator(self.schemaview.schema).serialize())


if __name__ == "__main__":
    pass
