"""
Anatomical Structure Translator

This module provides a class `AnS` which handles the processing and translation of anatomical structure data 
from CSV files into corresponding data objects. The data objects are then serialized into a JSON-LD format.

Classes:
    AnS: A class that processes CSV data files and generates anatomical structure objects.

Functions:
    cli: Command line interface for processing CSV files in a specified directory.

Usage:
    Run the script with a directory path containing CSV files as an argument to process the files 
    and generate anatomical structure objects.

Example:
    python anatomical_structure.py /path/to/csv_directory

Dependencies:
    csv: Provides functionality to read and write CSV files.
    inspect: Provides functions to inspect live objects.
    os: Provides a portable way of using operating system-dependent functionality.
    json: Provides functions to parse JSON.
    click: A package for creating command line interfaces.
    bkbit.models.anatomical_structure as ans: Import model for anatomical structures from bkbit.
"""

import csv
import inspect
import os
import json
import click
from bkbit.models import anatomical_structure as ans


class AnS:
    """
    AnS (Anatomical Structure) class

    This class provides functionality to read anatomical structure data from CSV files, generate appropriate
    data objects, and serialize them into JSON-LD format. The class supports various anatomical structures
    such as anatomical spaces, parcellation atlases, parcellation terms, and more.

    Attributes:
        anatomical_annotation_set (list): List to store anatomical annotation set objects.
        anatomical_space (list): List to store anatomical space objects.
        image_dataset (list): List to store image dataset objects.
        parcellation_annotation (list): List to store parcellation annotation objects.
        parcellation_annotation_term_map (list): List to store parcellation annotation term map objects.
        parcellation_atlas (list): List to store parcellation atlas objects.
        parcellation_color_assignment (list): List to store parcellation color assignment objects.
        parcellation_terminology (list): List to store parcellation terminology objects.
        parcellation_term_set (list): List to store parcellation term set objects.
        parcellation_term (list): List to store parcellation term objects.
        parcellation_color_scheme (list): List to store parcellation color scheme objects.
        func_header_mapping (dict): Dictionary mapping function headers to their corresponding functions.

    Methods:
        assign_func_header: Creates a mapping between function headers and their corresponding functions.
        read_data: Reads data from a CSV file and generates appropriate data objects.
        provide_data: Reads and processes CSV files from a specified directory path.
        generate_parcellation_atlas: Generates a parcellation atlas object.
        generate_anatomical_space: Generates an anatomical space object.
        generate_anatomical_annotation_set: Generates an anatomical annotation set object.
        generate_parcellation_annotation: Generates a parcellation annotation object.
        generate_parcellation_terminology: Generates a parcellation terminology object.
        generate_parcellation_term_set: Generates a parcellation term set object.
        generate_parcellation_term: Generates a parcellation term object.
        generate_parcellation_annotation_term_map: Generates a parcellation annotation term map object.
        generate_parcellation_color_scheme: Generates a parcellation color scheme object.
        generate_parcellation_color_assignment: Generates a parcellation color assignment object.
        generate_image_dataset: Generates an image dataset object.
        serialize_to_jsonld: Serializes the object and writes it to a JSON-LD file.
    """

    def __init__(self):
        self.anatomical_annotation_set = []
        self.anatomical_space = []
        self.image_dataset = []
        self.parcellation_annotation = []
        self.parcellation_annotation_term_map = []
        self.parcellation_atlas = []
        self.parcellation_color_assignment = []
        self.parcellation_terminology = []
        self.parcellation_term_set = []
        self.parcellation_term = []
        self.parcellation_color_scheme = []
        self.func_header_mapping = self.__class__.assign_func_header()

    @classmethod
    def assign_func_header(cls):
        """
        Creates a mapping between function headers to their corresponding functions.

        Returns:
            dict: A dictionary mapping filtered function parameters to their respective functions.
        """
        mapping = {}
        for f in dir(cls):
            func = getattr(cls, f)
            if inspect.isfunction(func):
                func_params = inspect.signature(func).parameters.keys()
                filtered_params = frozenset(
                    param for param in func_params if param != "self"
                )
                mapping[filtered_params] = func
        return mapping

    def read_data(self, file_name):
        """
        Reads data from a CSV file and generates appropriate data objects based on column names.

        Args:
            file_name (str): The name of the CSV file to read.

        Returns:
            None
        """
        with open(file_name, mode="r", encoding="utf-8") as file:
            # Create a CSV reader object
            reader = csv.reader(file)

            # Read the first row to get column names
            column_names = next(reader)
            # Find corresponding 'generate' function
            func = self.func_header_mapping.get(frozenset(column_names))
            if func:
                # Iterate through each row in the CSV file
                for row in reader:
                    # Create a dictionary to store key-value pairs for each row
                    row_data = {}
                    for column_name, data in zip(column_names, row):
                        row_data[column_name] = data
                    # Generate appropriate data object
                    func(self, **row_data)

    def provide_data(self, dir_path):
        """
        Reads and processes CSV files from the specified directory path.

        Args:
            dir_path (str): The path to the directory containing the CSV files.

        Returns:
            None
        """
        for file in os.listdir(dir_path):
            if file.endswith(".csv"):
                self.read_data(os.path.join(dir_path, file))
        self.serialize_to_jsonld()

    def generate_parcellation_atlas(
        self,
        label,
        name,
        description,
        specialization_of,
        revision_of,
        version,
        anatomical_space_label,
        anatomical_annotation_set_label,
        parcellation_terminology_label,
    ):
        """
        Generates a parcellation atlas object with the given parameters.

        Args:
            label (str): The ID of the parcellation atlas.
            name (str): The name of the parcellation atlas.
            description (str): The description of the parcellation atlas.
            specialization_of (str): The specialization of the parcellation atlas.
            revision_of (str): The revision of the parcellation atlas.
            version (str): The version of the parcellation atlas.
            anatomical_space_label (str): The label of the anatomical space associated with the parcellation atlas.
            anatomical_annotation_set_label (str): The label of the anatomical annotation set associated with the parcellation atlas.
            parcellation_terminology_label (str): The label of the parcellation terminology associated with the parcellation atlas.

        Returns:
            ParcellationAtlas: The generated parcellation atlas object.
        """
        parcellation_atlas = ans.ParcellationAtlas(
            id=label,
            name=name,
            description=description,
            specialization_of=specialization_of,
            revision_of=revision_of,
            version=version,
            has_anatomical_space=anatomical_space_label,
            has_anatomical_annotation_set=anatomical_annotation_set_label,
            has_parcellation_terminology=parcellation_terminology_label,
        )
        self.parcellation_atlas.append(parcellation_atlas)
        return parcellation_atlas

    def generate_anatomical_space(
        self, label, name, description, version, image_dataset_label
    ):
        """
        Generates an anatomical space object and appends it to the list of anatomical spaces.

        Args:
            label (str): The ID of the anatomical space.
            name (str): The name of the anatomical space.
            description (str): The description of the anatomical space.
            version (str): The version of the anatomical space.
            image_dataset_label (str): The label of the image dataset associated with the anatomical space.

        Returns:
            AnatomicalSpace: The generated anatomical space object.
        """
        anat_space = ans.AnatomicalSpace(
            id=label,
            name=name,
            description=description,
            version=version,
            measures=image_dataset_label,
        )
        self.anatomical_space.append(anat_space)
        return anat_space

    def generate_anatomical_annotation_set(
        self, label, name, description, revision_of, version, anatomical_space_label
    ):
        """
        Generates an anatomical annotation set.

        Args:
            label (str): The ID of the anatomical annotation set.
            name (str): The name of the anatomical annotation set.
            description (str): The description of the anatomical annotation set.
            revision_of (str): The ID of the anatomical annotation set that this set is a revision of.
            version (str): The version of the anatomical annotation set.
            anatomical_space_label (str): The label of the anatomical space that this set parameterizes.

        Returns:
            AnatomicalAnnotationSet: The generated anatomical annotation set.
        """
        anat_annot_set = ans.AnatomicalAnnotationSet(
            id=label,
            name=name,
            description=description,
            revision_of=revision_of,
            version=version,
            parameterizes=anatomical_space_label,
        )
        self.anatomical_annotation_set.append(anat_annot_set)
        return anat_annot_set

    def generate_parcellation_annotation(
        self, internal_identifier, anatomical_annotation_set_label, voxel_count
    ):
        """
        Generates a parcellation annotation object and adds it to the list of parcellation annotations.

        Args:
            internal_identifier (str): The internal identifier of the parcellation annotation.
            anatomical_annotation_set_label (str): The label of the anatomical annotation set that the parcellation annotation is part of.
            voxel_count (int): The voxel count of the parcellation annotation.

        Returns:
            ParcellationAnnotation: The generated parcellation annotation object.
        """
        parcellation_annotation = ans.ParcellationAnnotation(
            internal_identifier=internal_identifier,
            part_of_anatomical_annotation_set=anatomical_annotation_set_label,
            voxel_count=voxel_count,
        )
        self.parcellation_annotation.append(parcellation_annotation)
        return parcellation_annotation

    def generate_parcellation_terminology(
        self, label, name, description, revision_of, version
    ):
        """
        Generates a parcellation terminology object and appends it to the list of parcellation terminologies.

        Args:
            label (str): The label of the parcellation terminology.
            name (str): The name of the parcellation terminology.
            description (str): The description of the parcellation terminology.
            revision_of (str): The revision of the parcellation terminology.
            version (str): The version of the parcellation terminology.

        Returns:
            ParcellationTerminology: The generated parcellation terminology object.
        """
        parcellation_terminology = ans.ParcellationTerminology(
            id=label,
            name=name,
            description=description,
            revision_of=revision_of,
            version=version,
        )
        self.parcellation_terminology.append(parcellation_terminology)
        return parcellation_terminology

    def generate_parcellation_term_set(
        self,
        label,
        name,
        description,
        parcellation_terminology_label,
        parcellation_term_set_order,
        parcellation_parent_term_set_label,
    ):
        """
        Generates a parcellation term set object and adds it to the list of parcellation term sets.

        Args:
            label (str): The ID of the parcellation term set.
            name (str): The name of the parcellation term set.
            description (str): The description of the parcellation term set.
            parcellation_terminology_label (str): The label of the parcellation terminology that the term set belongs to.
            parcellation_term_set_order (int): The ordinal value of the parcellation term set.
            parcellation_parent_term_set_label (str): The label of the parent parcellation term set, if any.

        Returns:
            ParcellationTermSet: The generated parcellation term set object.

        """
        parcellation_term_set = ans.ParcellationTermSet(
            id=label,
            name=name,
            description=description,
            part_of_parcellation_terminology=parcellation_terminology_label,
            ordinal=parcellation_term_set_order,
            has_parent_parcellation_term_set=parcellation_parent_term_set_label,
        )
        self.parcellation_term_set.append(parcellation_term_set)
        return parcellation_term_set

    def generate_parcellation_term(
        self,
        name,
        symbol,
        description,
        parcellation_term_set_label,
        parcellation_terminology_label,
        parcellation_term_identifier,
        parcellation_term_order,
        parcellation_parent_term_set_label,
        parcellation_parent_term_identifier,
    ):
        """
        Generates a parcellation term object and adds it to the list of parcellation terms.

        Args:
            name (str): The name of the parcellation term.
            symbol (str): The symbol of the parcellation term.
            description (str): The description of the parcellation term.
            parcellation_term_set_label (str): The label of the parcellation term set.
            parcellation_terminology_label (str): The label of the parcellation terminology.
            parcellation_term_identifier (str): The identifier of the parcellation term.
            parcellation_term_order (int): The order of the parcellation term.
            parcellation_parent_term_set_label (str): The label of the parent parcellation term set.
            parcellation_parent_term_identifier (str): The identifier of the parent parcellation term.

        Returns:
            ans.ParcellationTerm: The generated parcellation term object.
        """
        parcellation_term = ans.ParcellationTerm(
            id=parcellation_term_identifier,
            name=name,
            symbol=symbol,
            description=description,
            part_of_parcellation_term_set=parcellation_term_set_label,
            ordinal=parcellation_term_order,
            has_parent_parcellation_term=parcellation_parent_term_identifier,
        )
        self.parcellation_term.append(parcellation_term)
        return parcellation_term

    def generate_parcellation_annotation_term_map(
        self,
        internal_identifier,
        anatomical_annotation_set_label,
        parcellation_term_identifier,
        parcellation_term_set_label,
        parcellation_terminology_label,
    ):
        """
        Generates a parcellation annotation term map.

        Args:
            internal_identifier (str): The internal identifier of the subject parcellation annotation.
            anatomical_annotation_set_label (str): The label of the anatomical annotation set.
            parcellation_term_identifier (str): The identifier of the subject parcellation term.
            parcellation_term_set_label (str): The label of the parcellation term set.
            parcellation_terminology_label (str): The label of the parcellation terminology.

        Returns:
            ParcellationAnnotationTermMap: The generated parcellation annotation term map.
        """
        parcellation_annotation_term_map = ans.ParcellationAnnotationTermMap(
            subject_parcellation_annotation=internal_identifier,
            subject_parcellation_term=parcellation_term_identifier,
        )
        self.parcellation_annotation_term_map.append(parcellation_annotation_term_map)
        return parcellation_annotation_term_map

    def generate_parcellation_color_scheme(
        self,
        label,
        name,
        description,
        revision_of,
        version,
        parcellation_terminology_label,
    ):
        """
        Generates a parcellation color scheme object and appends it to the list of parcellation color schemes.

        Args:
            label (str): The ID of the parcellation color scheme.
            name (str): The name of the parcellation color scheme.
            description (str): The description of the parcellation color scheme.
            revision_of (str): The ID of the parcellation color scheme that this scheme is a revision of.
            version (str): The version of the parcellation color scheme.
            parcellation_terminology_label (str): The label of the subject parcellation terminology.

        Returns:
            ParcellationColorScheme: The generated parcellation color scheme object.
        """
        parcellation_color_scheme = ans.ParcellationColorScheme(
            id=label,
            name=name,
            description=description,
            revision_of=revision_of,
            version=version,
            subject_parcellation_terminology=parcellation_terminology_label,
        )
        self.parcellation_color_scheme.append(parcellation_color_scheme)
        return parcellation_color_scheme

    def generate_parcellation_color_assignment(
        self,
        parcellation_color_scheme_label,
        parcellation_term_identifier,
        parcellation_terminology_label,
        color_hex_triplet,
    ):
        """
        Generates a parcellation color assignment.

        Args:
            parcellation_color_scheme_label (str): The label of the parcellation color scheme.
            parcellation_term_identifier (str): The identifier of the subject parcellation term.
            parcellation_terminology_label (str): The label of the parcellation terminology.
            color_hex_triplet (str): The color hex triplet.

        Returns:
            ParcellationColorAssignment: The generated parcellation color assignment.
        """
        parcellation_color_assignment = ans.ParcellationColorAssignment(
            part_of_parcellation_color_scheme=parcellation_color_scheme_label,
            subject_parcellation_term=parcellation_term_identifier,
            color=color_hex_triplet,
        )
        self.parcellation_color_assignment.append(parcellation_color_assignment)
        return parcellation_color_assignment

    def generate_image_dataset(
        self,
        label,
        name,
        description,
        revision_of,
        version,
        x_direction,
        y_direction,
        z_direction,
        x_size,
        y_size,
        z_size,
        x_resolution,
        y_resolution,
        z_resolution,
        unit,
    ):
        """
        Generates an image dataset object with the given parameters.

        Args:
            label (str): The ID of the image dataset.
            name (str): The name of the image dataset.
            description (str): The description of the image dataset.
            revision_of (str): The ID of the image dataset that this dataset is a revision of.
            version (str): The version of the image dataset.
            x_direction (str): The direction of the X-axis.
            y_direction (str): The direction of the Y-axis.
            z_direction (str): The direction of the Z-axis.
            x_size (float): The size of the X-axis.
            y_size (float): The size of the Y-axis.
            z_size (float): The size of the Z-axis.
            x_resolution (float): The resolution of the X-axis.
            y_resolution (float): The resolution of the Y-axis.
            z_resolution (float): The resolution of the Z-axis.
            unit (str): The unit of measurement.

        Returns:
            ans.ImageDataset: The generated image dataset object.
        """
        image_dataset = ans.ImageDataset(
            id=label,
            name=name,
            description=description,
            version=version,
            revision_of=revision_of,
            x_direction=getattr(ans.ANATOMICALDIRECTION, x_direction.replace("-", "_")),
            y_direction=getattr(ans.ANATOMICALDIRECTION, y_direction.replace("-", "_")),
            z_direction=getattr(ans.ANATOMICALDIRECTION, z_direction.replace("-", "_")),
            x_size=x_size,
            y_size=y_size,
            z_size=z_size,
            x_resolution=x_resolution,
            y_resolution=y_resolution,
            z_resolution=z_resolution,
            unit=getattr(ans.DISTANCEUNIT, unit),
        )
        self.image_dataset.append(image_dataset)
        return image_dataset

    def serialize_to_jsonld(
        self, exclude_none: bool = True, exclude_unset: bool = False
    ):
        """
        Serialize the object and write it to the specified output file.

        Parameters:

        Returns:
            None
        """
        data = []
        data.extend([obj.__dict__ for obj in self.anatomical_annotation_set])
        data.extend([obj.__dict__ for obj in self.anatomical_space])
        data.extend([obj.__dict__ for obj in self.image_dataset])
        data.extend([obj.__dict__ for obj in self.parcellation_annotation])
        data.extend([obj.__dict__ for obj in self.parcellation_annotation_term_map])
        data.extend([obj.__dict__ for obj in self.parcellation_atlas])
        data.extend([obj.__dict__ for obj in self.parcellation_color_assignment])
        data.extend([obj.__dict__ for obj in self.parcellation_color_scheme])
        data.extend([obj.__dict__ for obj in self.parcellation_terminology])
        data.extend([obj.__dict__ for obj in self.parcellation_term_set])
        data.extend([obj.__dict__ for obj in self.parcellation_term])

        output_data = {
            "@context": "https://raw.githubusercontent.com/brain-bican/models/main/jsonld-context-autogen/anatomical_structure.context.jsonld",
            "@graph": data,
        }
        print(json.dumps(output_data, indent=2))


@click.command()
@click.argument("dir_path", type=str)
def cli(dir_path):
    """
    Command line interface for the Anatomical Structure Translator.

    Parameters:
        dir_path (str): Path to the directory containing CSV files.

    Returns:
        None
    """
    translator = AnS()
    translator.provide_data(dir_path)


if __name__ == "__main__":
    cli()
