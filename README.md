Requirements and usage examples are at the bottom of this

My basic insight for the submission here is that the problem statement is effectively defining a grammar and asking for DSL parser. The only way I've learned how to do this was back in my undergraduate compilers course and so I applied simple versions of the same foundational ideas. We outline our grammer (below), tokenize the input, use a recursive descent parser to create a token abstract syntax tree with respect to our grammatical rules, then postorder traverse the AST to return the desired SQL string representation in a bottom up fashion.

I realized at the end that I forgot to plan for literal extensibility so that's currently unsupported. I also ran out of time to really attempt the query optimization bonus.

```
WHERE   := [OP ARG+]
OP      := AND | OR | NOT | < | > | = | != | is-empty | not-empty
ARG     := SCALAR | WHERE
SCALAR  := FIELD | LITERAL | NIL
AND     := WHERE | WHERE WHERE
OR      := WHERE WHERE
NOT     := WHERE
=       := SCALAR SCALAR+
!=      := SCALAR SCALAR+
<       := SCALAR SCALAR
>       := SCALAR SCALAR
is-empty := SCALAR
not-empty := SCALAR
FIELD   := UNSIGNED_INT
```

### Conceptual Flow
```
Start
└── Preprocess the submitted {<where-clause>, <limit>} into <where> and <limit> parts
    └── Tokenize the raw where-clause str into a list of tuples e.g. (<TOKEN_ID>, <VAL>)
        └── Rescursive descent on our tokens list to construct an abstract syntax tree, or token AST
            └── Do a postorder traversal on the token AST to combine individual node string representations bottom up
```
Which basically translates to:
```
DSLParser.generate_sql(...)
└── DSLParser._parse_clauses(...)
    └── DSLParser.tokenize(...) -> tokens
        └── DSLParser.parse_where(tokens) -> AST
            └── ASTSerializer.postorder_ast(AST.root) -> result
```

### Things to Improve
- The three weakest parts of this in its current form I would say are:
  1. The interface for extending operators and dialects
      - The dialect extension logic I think maybe works okay but it just feels bad to me
      - The operator extension logic I think is fundamentally confused. It requires far too much inner working knowlege of `DSLParser` / `ASTSerializer`
  2. The special preprocessing for `<where-clause>` and `<limit>`
      - I think ideally the where and limit clauses should be baked into the grammar so that their transpilation follows the same code path as e.g. operators
  3. Null handling
      - I think robust support for `nil` in the input string is missing. With more time I would do this differently
- I think the IN / NOT IN logic for `:=` and `:!=` is likely broken, and probably breaks whenever the list isn't `int`s
- Error handling leaves a lot to be desired
- Test suite is not exhaustive

### Requirements
```bash
(p) tplude~ python -V
Python 3.8.10
```

### Running tests
```bash
(p) tplude~ python -m unittest tests.py
..........
----------------------------------------------------------------------
Ran 10 tests in 0.001s

OK
```

### Usage
```python
from dsl_parser import DSLParser

fields = {
  1: "id",
  2: "name",
  3: "date_joined",
  4: "age"
}

p = DSLParser()
print(p.generate_sql(dialect='postgres', fields=fields, query='{:where [:= [:field 3] nil]}'))
# ;:: -> "SELECT * FROM data WHERE "date_joined" IS NULL;"
```

### Extending dialect
- We add new dialect support through `DSLParser.add_dialect(dialect_name, dialect_rules)`
- Basic supported rules can be seen in `ASTSerializer.DEFAULT_DIALECT_PARAMS`

```python
p.add_dialect('test', {'neq': '%', 'field-delim': '_'})

print(p.generate_sql(dialect='test', fields=fields, query='{:where [:or [:!= [:field 3] "2015-11-01"] [:= [:field 1] 456]]}'))
# ;:: -> "SELECT * FROM data WHERE _date_joined_ % \'2015-11-01\' OR _id_ = 456;"
```

### Extending operators
  - To extend the supported DSLParser operators you use `DSLParser.add_operator(op_id, parse_func, serialize_func)`
  - `op_id` is e.g. `:eq`
  - `parse_func` is a function that extends DSLParser's internal mechanisms for recognizing the new operator tokens
  - `serialize_func` is a function that extends ASTSerializer's internal mechanisms for converting AST token nodes to string representations

```python
def op_like_parse_func(dsl_parser):
  # Parse LIKE operator :like
  # Expects exactly two literals
  l = dsl_parser.parse_literal()
  r = dsl_parser.parse_literal()
  if not l or not r:
    raise SyntaxError('Expected 2 literal args to ":like"')
  return Node('DSL_OP', ':like', l, r)

def op_like_serialize_func(ast_serializer, node, l_str, r_str):
  return l_str + " LIKE " + r_str

p.add_operator(':like', parse_func=op_like_parse_func, serialize_func=op_like_serialize_func)

print(p.generate_sql(dialect='postgres', fields=fields, query='{:where [:like [:field 3] "foo%"]}'))
# ;:: -> "SELECT * FROM data WHERE "date_joined" LIKE '2012-%';"
```

### Using macros
```python

macros = {
  'outer_and': '[:and [:< [:field 1] 5] [:= [:field 2] "joe"]]',
  'inner_or': '[:< [:field 1] 5]',
  'inner_eq': '[:= [:field 2] "joe"]',
}

print(p.generate_sql(dialect='postgres', fields=fields, query='{:where [:macro "outer_and"]}', macros=macros))
# ;:: -> "SELECT * FROM data WHERE "id" < 5 AND "name" = 'joe';"
```
