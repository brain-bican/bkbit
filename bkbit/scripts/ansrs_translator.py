import csv
import inspect
import os
import json
from bkbit.models import ansrs

class AnSRS():
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
        mapping = {}
        for f in dir(cls):
            func = getattr(cls, f)
            if inspect.isfunction(func):
                func_params = inspect.signature(func).parameters.keys()
                filtered_params = frozenset(param for param in func_params if param != 'self')
                mapping[filtered_params] = func
        return mapping


    def read_data(self, file_name):

        with open(file_name, mode='r', encoding='utf-8') as file:
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
                    
    def provide_data(self, dir_path, output_file_name):
        for file in os.listdir(dir_path):
            if file.endswith(".csv"):
                self.read_data(os.path.join(dir_path, file))
        jsonld_file = os.path.join(dir_path, output_file_name)
        self.serialize_to_jsonld(jsonld_file)



    def generate_parcellation_atlas(self, label,name,description,specialization_of,revision_of,version,anatomical_space_label,anatomical_annotation_set_label,parcellation_terminology_label):
        parcellation_atlas = ansrs.ParcellationAtlas(id=label, name=name, description=description, specialization_of=specialization_of, revision_of=revision_of, version=version, has_anatomical_space=anatomical_space_label, has_anatomical_annotation_set=anatomical_annotation_set_label, has_parcellation_terminology=parcellation_terminology_label)
        self.parcellation_atlas.append(parcellation_atlas)
        return parcellation_atlas

    def generate_anatomical_space(self, label, name, description, version, image_dataset_label):
        anat_space = ansrs.AnatomicalSpace(id=label, name=name, description=description, version=version, measures=image_dataset_label)
        self.anatomical_space.append(anat_space)
        return anat_space

    def generate_anatomical_annotation_set(self, label, name, description, revision_of, version, anatomical_space_label):
        anat_annot_set = ansrs.AnatomicalAnnotationSet(id=label, name=name, description=description, revision_of=revision_of, version=version, parameterizes=anatomical_space_label)
        self.anatomical_annotation_set.append(anat_annot_set)
        return anat_annot_set

    def generate_parcellation_annotation(self, internal_identifier, anatomical_annotation_set_label, voxel_count):
        parcellation_annotation = ansrs.ParcellationAnnotation(internal_identifier=internal_identifier, part_of_anatomical_annotation_set=anatomical_annotation_set_label, voxel_count=voxel_count)
        self.parcellation_annotation.append(parcellation_annotation)
        return parcellation_annotation


    def generate_parcellation_terminology(self, label, name, description, revision_of, version):    
        parcellation_terminology = ansrs.ParcellationTerminology(id=label, name=name, description=description, revision_of=revision_of, version=version)
        self.parcellation_terminology.append(parcellation_terminology)
        return parcellation_terminology
    
    def generate_parcellation_term_set(self, label, name, description, parcellation_terminology_label, parcellation_term_set_order, parcellation_parent_term_set_label):
        parcellation_term_set = ansrs.ParcellationTermSet(id=label, name=name, description=description, part_of_parcellation_terminology=parcellation_terminology_label, ordinal=parcellation_term_set_order, has_parent_parcellation_term_set=parcellation_parent_term_set_label)
        self.parcellation_term_set.append(parcellation_term_set)
        return parcellation_term_set
    
    def generate_parcellation_term(self, name, symbol, description, parcellation_term_set_label, parcellation_terminology_label, parcellation_term_identifier, parcellation_term_order, parcellation_parent_term_set_label, parcellation_parent_term_identifier):
        parcellation_term = ansrs.ParcellationTerm(id=parcellation_term_identifier, name=name, symbol=symbol, description=description, part_of_parcellation_term_set = parcellation_term_set_label, ordinal = parcellation_term_order, has_parent_parcellation_term = parcellation_parent_term_identifier)
        self.parcellation_term.append(parcellation_term)
        return parcellation_term
    
    def generate_parcellation_annotation_term_map(self, internal_identifier,anatomical_annotation_set_label,parcellation_term_identifier,parcellation_term_set_label,parcellation_terminology_label):
        parcellation_annotation_term_map = ansrs.ParcellationAnnotationTermMap(subject_parcellation_annotation=internal_identifier, subject_parcellation_term=parcellation_term_identifier)
        self.parcellation_annotation_term_map.append(parcellation_annotation_term_map)
        return parcellation_annotation_term_map
    
    def generate_parcellation_color_scheme(self, label, name, description, revision_of, version, parcellation_terminology_label):
        parcellation_color_scheme = ansrs.ParcellationColorScheme(id=label, name=name, description=description, revision_of=revision_of, version=version, subject_parcellation_terminology=parcellation_terminology_label)
        self.parcellation_color_scheme.append(parcellation_color_scheme)
        return parcellation_color_scheme
    
    def generate_parcellation_color_assignment(self, parcellation_color_scheme_label,parcellation_term_identifier,parcellation_terminology_label,color_hex_triplet):
        parcellation_color_assignment = ansrs.ParcellationColorAssignment(part_of_parcellation_color_scheme=parcellation_color_scheme_label, subject_parcellation_term=parcellation_term_identifier, color=color_hex_triplet)
        self.parcellation_color_assignment.append(parcellation_color_assignment)
        return parcellation_color_assignment
    
    def generate_image_dataset(self, label, name, description, revision_of, version, x_direction, y_direction, z_direction, x_size, y_size, z_size, x_resolution, y_resolution, z_resolution, unit):
        image_dataset = ansrs.ImageDataset(id=label, name=name, description=description, version=version, revision_of=revision_of, x_direction=getattr(ansrs.ANATOMICALDIRECTION, x_direction.replace('-','_')), y_direction=getattr(ansrs.ANATOMICALDIRECTION, y_direction.replace('-', '_')), z_direction=getattr(ansrs.ANATOMICALDIRECTION, z_direction.replace('-', '_')), x_size=x_size, y_size=y_size, z_size=z_size, x_resolution=x_resolution, y_resolution=y_resolution, z_resolution=z_resolution, unit=getattr(ansrs.DISTANCEUNIT, unit))
        self.image_dataset.append(image_dataset)
        return image_dataset


    
    def serialize_to_jsonld(
        self, output_file: str, exclude_none: bool = True, exclude_unset: bool = False
    ):
        """
        Serialize the object and write it to the specified output file.

        Parameters:
            output_file (str): The path of the output file.

        Returns:
            None
        """
        with open(output_file, "w", encoding="utf-8") as f:
            data = []
            # for obj in self.generated_objects.values():
            #     # data.append(obj.to_dict(exclude_none=exclude_none, exclude_unset=exclude_unset))
            #     data.append(obj.__dict__)
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
                "@context": "https://raw.githubusercontent.com/puja-trivedi/models/ansrs_model_puja_version/jsonld-context-autogen/ansrs_schema.context.jsonld",
                "@graph": data,
            }
            f.write(json.dumps(output_data, indent=2))
    

    

