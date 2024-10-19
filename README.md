Sections should be:

`requirements`

`usage.py`

`extending dialect`

`extending operators`

`extending literals`

`macros usage`

!! TODO

- Extend literal type support

!! NOTES

- I think the IN / NOT IN logic for := and :!= breaks down with literal types that are not `int`, e.g. single quoted strings, nils,
- Revisit the function maps inside ASTSerializer. General idea I think is okay but the specific implementation seems not ideal
- Support for :where and :limit is pretty rigid. In a more robust parser I think this should be reworked to be more inherently supported by the tokenizer and parser
- Better error handling
