import kbmodel
import json 

definitions = {
    "GeneAnnotation": kbmodel.GeneAnnotation.model_json_schema(ref_template="#/definitions/{model}"),
    "GenomeAnnotation": kbmodel.GenomeAnnotation.model_json_schema(ref_template="#/definitions/{model}"),
    "GenomeAssembly": kbmodel.GenomeAssembly.model_json_schema(ref_template="#/definitions/{model}"),
    "OrganismTaxon": kbmodel.OrganismTaxon.model_json_schema(ref_template="#/definitions/{model}"),
    "CheckSum": kbmodel.Checksum.model_json_schema(ref_template="#/definitions/{model}"),
    "BioType": {
        "title": "BioType",
        "type": "string",
        "enum": [member.value for member in kbmodel.BioType],
    },
    "DigestType": {
        "title": "DigestType",
        "type": "string",
        "enum": [member.value for member in kbmodel.DigestType],
    },
    "AuthorityType": {
        "title": "AuthorityType",
        "type": "string",
        "enum": [member.value for member in kbmodel.AuthorityType],
    },
}

# Save all JSON schemas to a single file
with open("kbmodel_gars.json", 'w') as file:
    json.dump(definitions, file, indent=2)