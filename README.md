# Brain Knowledge Base Interaction Toolkit

This package contains [Pydantic](https://docs.pydantic.dev/latest/) version of the [BICAN Knowledgebase Data Models](https://github.com/brain-bican/models),
 along with tools to interact with the models and the data they represent.

This project is still under development, and we encourage everyone to provide feedback and join the project.
## Models
All models are located in the [models directory](./bkbit/models). Currently, we support the following models:

- [Library Generation Model](https://brain-bican.github.io/models/index_library_generation/)
- [Anatomical Structure Model](https://brain-bican.github.io/models/index_anatomical_structure/)
- [Genome Annotation Model](https://brain-bican.github.io/models/index_genome_annotation/)



## Tools to interact with the models

- [Tools to extract data, validate against the current model, and create JSON-LD representations](./bkbit/data_translators/README.md)
- [Converter from spreadsheets to LinkML YAML files](./bkbit/model_converters/README.md)
- [Tools to edit LinkML YAML files](./bkbit/model_editors/README.md)

## Installation

### Installation from PyPI
```bash
pip install bkbit
```
#### Temporary fix: updating to new schemasheets version from GitHub:
```commandline
pip install git+https://github.com/linkml/schemasheets
```

### Instructions for developers:
- Fork the repository
- Clone your fork
- Navigate to the main project directory: `cd bkbit`
- Install in editable mode: `pip install -e .[all]`
- Install newer version of schemasheets (temporary fix): `pip install git+https://github.com/linkml/schemasheets`