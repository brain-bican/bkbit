# specimen2jsonld

<b>*specimen2jsonld*</b> generates BICAN objects for specimen record(s) and its respective ancestors or descendants using data from the [Specimen Portal](https://brain-specimenportal.org/). 

## Docs

### Command Line
#### bkbit specimen2jsonld

```python
bkbit specimen2jsonld [OPTIONS] NHASH_ID_OR_FILE
```

#### Options
<span style="color: red;">-d, --descendants</span> <br> 
&emsp;Generate BICAN objects for the given NHASH_ID and all of its descendants. <br>

#### Arguments
<span style="color: red;">NHASH_ID_OR_FILE</span> <br> 
&emsp;Required argument. Provide either a nhash_id of a record or a file containing nhash_id(s).<br>

### Examples
#### Example 1: Parse a <b>single</b> record and its ancestors 
```python
# Install bkbit 
pip install bkbit

# Set SpecimenPortal Personal API Token
export jwt_token='specimen_portal_personal_api_token'

# Run speciment2jsonld command 
bkbit specimen2jsonld 'LP-CVFLMQ819998' > output.jsonld
```

#### Example 2: Parse a <b>single</b> containing record(s) and its descendants  
```python
# Install bkbit 
pip install bkbit

# Set SpecimenPortal Personal API Token
export jwt_token='specimen_portal_personal_api_token'

# Run speciment2jsonld command 
bkbit specimen2jsonld -d 'DO-GICE7463' > output.jsonld
```

#### Example 3: Parse a <b>file</b> containing record(s) and their respective ancestors 
```python
# Install bkbit 
pip install bkbit

# Set SpecimenPortal Personal API Token
export jwt_token='specimen_portal_personal_api_token'

# Contents of input file 
cat input_nhash_ids.txt

LA-TZWCWB265559FVVNTS329147
LA-IAXCCV360563HBFKKM103455
LA-JFCEST535498UIPMOH349083

# Run speciment2jsonld command 
bkbit specimen2jsonld input_nhash_ids.txt 

# Expected output 
ls .

LA-TZWCWB265559FVVNTS329147.jsonld
LA-IAXCCV360563HBFKKM103455.jsonld
LA-JFCEST535498UIPMOH349083.jsonld
```


#### Example 4: Parse a <b>file</b> containing multiple records and their respective descendants 
```python
# Install bkbit 
pip install bkbit

# Set SpecimenPortal Personal API Token
export jwt_token='specimen_portal_personal_api_token'

# Contents of input file 
cat input_nhash_ids.txt

DO-XIQQ6047
DO-WFFF3774
DO-RMRL6873

# Run speciment2jsonld command 
bkbit specimen2jsonld -d input_nhash_ids.txt 

# Expected output 
ls .

DO-XIQQ6047.jsonld
DO-WFFF3774.jsonld
DO-RMRL6873.jsonld
```