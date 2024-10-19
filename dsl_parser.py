
from utils import has_cycle, reduce_macros


DEFAULT_FIELDS = {
  1: "id",
  2: "name",
  3: "date_joined",
  4: "age"
}


class ASTSerializer():
  """
  ASTSerializer takes an Abstract Syntax Tree (AST) built by DSLParser and outputs
  its sql query string representation with respect to the configured dialect
  """

  DEFAULT_DIALECT_PARAMS = {
    'neq': '<>',
    'field-delim': '"',
    'template': "SELECT * FROM data {where_str} {limit_str}",
    'limit_template': 'LIMIT {limit}'
  }

  def __init__(self, dialect = 'postgres', fields = DEFAULT_FIELDS):
    self.dialect = dialect
    self.fields = fields
    self.added_operators = []

    self.dialect_rules = {
      'postgres': {
        'neq': '<>',
        'field-delim': '"',
        'template': "SELECT * FROM data {where_str} {limit_str}",
        'limit_template': 'LIMIT {limit}',
      },
      'mysql': {
        'neq': '<>',
        'field-delim': "`",
        'template': "SELECT * FROM data {where_str} {limit_str}",
        'limit_template': 'LIMIT {limit}',
      },
      'sqlserver': {
        'neq': '<>',
        'field-delim': '"',
        'template': "SELECT {limit_str} * FROM data {where_str}",
        'limit_template': 'TOP {limit}',
      }
    }

    self.leaf_to_str_map = {
      'DSL_FIELD': self.serialize_field,
      'DSL_LITERAL': self.serialize_literal,
      'DSL_NIL': self.serialize_nil,
      'DSL_LIST': self.serialize_list,
    }

    self.node_to_str_map = {
      'DSL_OP': self.serialize_op,
    }

    self.operator_to_str_map = {
      ':and': self.serialize_and,
      ':or': self.serialize_or,
      ':not': self.serialize_not,
      ':=': self.serialize_eq,
      ':!=': self.serialize_neq,
      ':<': self.serialize_lt,
      ':>': self.serialize_gt,
      ':in': self.serialize_in,
      ':not-in': self.serialize_not_in,
      ':is-empty': self.serialize_is_empty,
      ':not-empty': self.serialize_not_empty,
    }

  def set_dialect(self, dialect):
    if dialect not in self.dialect_rules:
      raise RuntimeError(f'Unsupported dialect "{dialect}"')
    self.dialect = dialect

  def set_fields(self, fields):
    self.fields = fields

  def add_dialect(self, name, params):
    if name in self.dialect_rules:
      raise RuntimeWarning(f'Overwriting dialect rules for {name}')
    self.dialect_rules[name] = {
      **ASTSerializer.DEFAULT_DIALECT_PARAMS,
      **params,
    }

  def add_operator(self, op_id, serialize_func):
    if op_id in self.operator_to_str_map:
      raise Exception(f'ASTSerializer operator exists with id: "{op_id}"')
    self.added_operators.append(op_id)
    self.operator_to_str_map[op_id] = serialize_func

  def _get_field_delim(self):
    return self.dialect_rules.get(self.dialect, {}).get('field-delim', "'")

  def serialize_op(self, node, l_str, r_str):
    if node.value in self.added_operators:
      return self.operator_to_str_map[node.value](self, node, l_str, r_str)
    return self.operator_to_str_map[node.value](node, l_str, r_str)

  def serialize_field(self, node):
    d = self._get_field_delim()
    return(f'{d}{self.fields[int(node.value)]}{d}')

  def serialize_literal(self, node):
    # @TODO: Improve robustness of string literal checking
    if node.value.startswith('"'):
      tmp = node.value.strip('"')
      return(f"'{tmp}'")
    return(node.value)

  def serialize_nil(self, node):
    return("NULL")
  
  def serialize_list(self, node):
    tmp = ", ".join(node.value)
    return(f"({tmp})")

  def _has_nested(self, node):
    # @TODO: Document usage
    if not node:
      return False
    return node.value in [':or', ':and']

  def serialize_and(self, node, l_str, r_str):
    if self._has_nested(node.left):
      l_str = f"({l_str})"
    if self._has_nested(node.right):
      r_str = f"({r_str})"
    return l_str + " AND " + r_str

  def serialize_or(self, node, l_str, r_str):
    if self._has_nested(node.left):
      l_str = f"({l_str})"
    if self._has_nested(node.right):
      r_str = f"({r_str})"
    return l_str + " OR " + r_str

  def serialize_not(self, node, l_str, r_str):
    # @NOTE: Code smell, this depends on the fact that our AST parser only populates left child for :not
    return " NOT " + l_str

  def serialize_eq(self, node, l_str, r_str):
    # @TODO: Handle if both children of :eq are NULL?
    if (l_str and l_str != "NULL") and r_str == "NULL":
      return l_str + " IS NULL"
    elif l_str == "NULL" and (r_str and r_str != "NULL"):
      return r_str + " IS NULL"
    return l_str + " = " + r_str

  def serialize_neq(self, node, l_str, r_str):
    if (l_str and l_str != "NULL") and r_str == "NULL":
      return l_str + " IS NOT NULL"
    elif l_str == "NULL" and (r_str and r_str != "NULL"):
      return r_str + " IS NOT NULL"
    neq = self.dialect_rules[self.dialect].get('neq', '<>')
    return " ".join([l_str, neq, r_str])

  def serialize_is_empty(self, node, l_str, r_str):
    # @NOTE: Code smell, this depends on the fact that our AST parser only populates left child for :is-empty
    return "IS NULL " + l_str

  def serialize_not_empty(self, node, l_str, r_str):
    # @NOTE: Code smell, this depends on the fact that our AST parser only populates left child for :not-empty
    return "IS NOT NULL " + l_str

  def serialize_lt(self, node, l_str, r_str):
    return l_str + " < " + r_str

  def serialize_gt(self, node, l_str, r_str):
    return l_str + " > " + r_str

  def serialize_in(self, node, l_str, r_str):
    return l_str + " IN " + r_str

  def serialize_not_in(self, node, l_str, r_str):
    return l_str + " NOT IN " + r_str

  def postorder_ast(self, node):
    """
    Post order AST traversal for serializing SQL query with respect to selected dialect
    This is the meat of this class
    """
    if not node:
      return None
    
    if node.is_leaf():
      return self.leaf_to_str_map[node.type](node)
    
    l_str = self.postorder_ast(node.left)
    r_str = self.postorder_ast(node.right)
    return self.node_to_str_map[node.type](node, l_str, r_str)
  
  def _get_template(self):
    default = "SELECT * FROM data WHERE {where_str} {limit_str}"
    return self.dialect_rules.get(self.dialect, {}).get('template', default)

  def _get_limit_str(self, limit):
    if limit is None:
      return ""
    tmp = self.dialect_rules.get(self.dialect, {}).get('limit_template', 'LIMIT {limit}')
    return tmp.format(limit=limit)

  def serialize_ast(self, ast, limit = None):
    """
    Take AST and return its SQL query string representation
    """
    template = self._get_template()
    limit_str = self._get_limit_str(limit)
    # @NOTE This final formatting of the result is.. let's say.. not ideal
    where_str = "WHERE " + self.postorder_ast(ast) if ast is not None else ""
    return template.format(where_str=where_str, limit_str=limit_str).replace('  ', ' ').strip() + ";"


class Node:
  """
  Building block class for composing ASTs generated by DSLParser
  """
  def __init__(self, type, value, left = None, right = None):
    self.type = type
    self.value = value
    self.left = left
    self.right = right

  def is_leaf(self):
    return self.left is None and self.right is None

  def __str__(self):
    return(f"Node({self.type},{self.value},{self.left},{self.right})")

  def __repr__(self):
    return(f"Node({self.type},{self.value},{self.left},{self.right})")


class DSLParser:
  def __init__(self):
    self.serializer = ASTSerializer()
    self.added_operators = []
    self.tokens = None
    self.current = None
    self.operators = {
      ':and': self.parse_and,
      ':or': self.parse_or,
      ':not': self.parse_not,
      ':=': self.parse_op_equals,
      ':!=': self.parse_op_not_equals,
      ':<': self.parse_op_lt,
      ':>': self.parse_op_gt,
      ':is-empty': self.parse_is_empty,
      ':not-empty': self.parse_not_empty,
    }

  def set_tokens(self, tokens):
    self.tokens = iter(tokens)
    self.current = next(self.tokens, None)

  def advance(self):
    self.current = next(self.tokens, None)

  def accept(self, token):
    if self.current[0] == token:
      self.advance()
      return True
    return False
  
  def expect(self, token):
    if self.current[0] == token:
      self.advance()
      return True
    else:
      raise SyntaxError(f'Expected {token}')

  def parse_field(self):
    c = self.current
    if self.accept('DSL_FIELD'):
      return Node('DSL_FIELD', c[1], None, None)
    return None

  def parse_literal(self):
    # LITERAL := SCALAR | FIELD | NIL
    c = self.current
    n = None
    if self.accept('DSL_LITERAL'):
      n = Node('DSL_LITERAL', c[1], None, None)
    elif self.accept('DSL_FIELD'):
      n = Node('DSL_FIELD', c[1], None, None)
    elif self.accept('DSL_NIL'):
      n = Node('DSL_NIL', None, None, None)
    return n

  def parse_op_equals(self):
    # Parse equals operator :=
    # Expects 2 or more literals
    l = self.parse_literal()
    r = self.parse_literal()
    args = []
    while r is not None:
      args.append(r)
      r = self.parse_literal()
    
    res = None
    if len(args) > 1:
      # We have an "IN" operator
      r = Node('DSL_LIST', [x.value for x in args], None, None)
      res = Node('DSL_OP', ':in', l, r)
    else:
      # We have an "EQUALS" operator
      res = Node('DSL_OP', ':=', l, args[0])
    return res

  def parse_op_not_equals(self):
    # Parse not equals operator :!=
    # Expects 2 or more literals
    l = self.parse_literal()
    r = self.parse_literal()
    args = []
    while r is not None:
      args.append(r)
      r = self.parse_literal()
    
    res = None
    if len(args) > 1:
      # We have a "NOT IN" operator
      r = Node('DSL_LIST', [x.value for x in args], None, None)
      res = Node('DSL_OP', ':not-in', l, r)
    else:
      # We have an "NOT EQUALS" operator
      res = Node('DSL_OP', ':!=', l, args[0])
    return res

  def parse_op_lt(self):
    # Parse less than operator :<
    # Expects exactly two literals
    l = self.parse_literal()
    r = self.parse_literal()
    if not l or not r:
      raise SyntaxError('Expected 2 literal args to ":<"')
    return Node('DSL_OP', ':<', l, r)

  def parse_op_gt(self):
    # Parse greater than operator :>
    # Expects exactly two literals
    l = self.parse_literal()
    r = self.parse_literal()
    if not l or not r:
      raise SyntaxError('Expected 2 literal args to ":>"')
    return Node('DSL_OP', ':>', l, r)

  def parse_is_empty(self):
    # Parse is empty operator :is-empty
    # Expects exactly one literal
    l = self.parse_literal()
    if not l:
      raise SyntaxError('Expected 1 literal arg to :is-empty')
    return Node('DSL_OP', ':is-empty', l, None)

  def parse_not_empty(self):
    # Parse not empty operator :not-empty
    # Expects exactly one literal
    l = self.parse_literal()
    if not l:
      raise SyntaxError('Expected 1 literal arg to :not-empty')
    return Node('DSL_OP', ':not-empty', l, None)

  def parse_and(self):
    # Parse AND operator :and
    # EITHER:
    # :and <where>
    # :and <where> <where>
    l = self.parse_where()
    if not l:
      raise SyntaxError('Expected 1-2 WHERE clauses following :and, got 0')
    r = self.parse_where()
    return Node('DSL_OP', ':and', l, r)

  def parse_or(self):
    # Parse OR operator :or
    # :or <where> <where>
    l = self.parse_where()
    r = self.parse_where()
    if not l or not r:
      raise SyntaxError('Expected 2 WHERE clauses following :or')
    return Node('DSL_OP', ':or', l, r)

  def parse_not(self):
    # Parse NOT operator :not
    # :not <where>
    l = self.parse_where()
    if not l:
      raise SyntaxError('Expected 1 WHERE clause following :not')
    return Node('DSL_OP', ':not', l, None)

  def parse_op(self):
    # Parse operator
    c = self.current
    self.expect('DSL_OP')
    if c[1] in self.added_operators:
      return self.operators[c[1]](self)
    return self.operators[c[1]]()

  def parse_where(self):
    n = None
    if self.accept('DSL_OPEN_BRACKET'):
      n = self.parse_op()
      self.expect('DSL_CLOSE_BRACKET')
    return n
  
  def tokenize(self, raw):
    """
    This is our tokenizer / lexer for the input where-clause query that returns a list of tokens to
    be consumed by our DSLParser in the construction of an AST

    :param `raw`: A where-clause string
    :returns: A list of tuples of the form (Str(TOKEN_TYPE), TOKEN_VALUE))
    """
    tokens = []

    def has_flattenable_field(tokens):
      """
      @NOTE:
      By default FIELD tokens end up in the token stream sandwiched between open & close BRACKET tokens
      This helper removes the book end bracket tokens to make the parser's life easier
      The existence of this helper is probably indicating that the overall grammer / tokenizer is suboptimal
      """
      return len(tokens) >= 3 and all([
        tokens[-3][0] == 'DSL_OPEN_BRACKET',
        tokens[-2][0] == 'DSL_FIELD',
        tokens[-1][0] == 'DSL_CLOSE_BRACKET'
      ])

    i = 0
    while i < len(raw):
      if raw[i] == "[":
        tokens.append(('DSL_OPEN_BRACKET', '['))
        i += 1
        continue
      elif raw[i] == "]":
        tokens.append(('DSL_CLOSE_BRACKET', ']'))
        if has_flattenable_field(tokens):
          # Flatten DSL_FIELDs that are wrapped by open/close brackets
          field_token = tokens[-2]
          tokens = tokens[:-3] + [field_token]
        i += 1
        continue
      elif raw[i] == ":":
        idx = raw[i:].find(' ')
        tmp = raw[i:][:idx]
        if tmp == ":field":
          # process field
          k = idx + 1 # first digit of field identifier
          while k < len(raw) and raw[i:][k].isdigit():
            k += 1
          tokens.append(('DSL_FIELD', raw[i:][idx+1:k]))
          i += k
          continue
        else:
          # @TODO: Check if supported operator, else error
          tokens.append(('DSL_OP', tmp))
          i += idx + 1
      elif raw[i] == " ":
        i += 1
        continue
      else:
        # Consuming a literal
        k = i + 1
        while k < len(raw) and raw[k] not in [x for x in " []{}"]:
          k += 1
        tmp = raw[i:k]
        if tmp == "nil":
          tokens.append(('DSL_NIL', tmp))
        else:
          tokens.append(('DSL_LITERAL', raw[i:k]))
        i = k
    return tokens

  def _parse_clauses(self, raw_query):
    res = {'where': None, 'limit': None}
    if not (raw_query.startswith('{') and raw_query.endswith('}')):
      raise SyntaxError('Did not find opening and/or closing bracket "{" | "}"')
    
    def split_clause(raw):
      # @TODO: Handle if raw has no space (malformed input)
      idx = raw.find(' ')
      return (raw[:idx], raw[idx + 1:])
    for key, val in [split_clause(x.strip()) for x in raw_query.strip('{}').split(',')]:
      if key == ":where":
        if res['where'] is not None:
          raise Exception('Expected at most 1 `where` clause')
        res['where'] = val
      elif key == ':limit':
        if res['limit'] is not None:
          raise Exception('Expected at most 1 `limit` clause')
        if not val.isdigit():
          raise Exception(f'Expected unsigned int value for `limit`, got {val}')
        res['limit'] = int(val)
    return((res['where'], res['limit']))

  def add_operator(self, op_id, parse_func, serialize_func):
    """
    Extend DSLParser with new where-clause operator support
    :param id: An operator id of the form `:<str>` e.g. `:like`
    :param parse_func: A function to extend the DSLParser for creating new DSL_OP nodes in the AST
    :param serialize_func: A function to extend the ASTSerializer for string formatting the new DSL_OP AST nodes
    """
    if op_id in self.operators:
      raise Exception(f'DSLOperator operator exists with id: "{op_id}"')
    self.operators[op_id] = parse_func
    self.added_operators.append(op_id)
    self.serializer.add_operator(op_id, serialize_func)

  def add_dialect(self, name, params):
    self.serializer.add_dialect(name, params)

  def resolve_macros(self, raw_where, macros):
    """
    Takes a raw <where-clause> string and iteratively flattens the macro references
    """
    if has_cycle(macros):
      raise RuntimeError("Cycle detected in macros.")
    return reduce_macros(raw_where, macros)

  def generate_sql(self, dialect, fields, query, macros={}):
    """
    The primary solution method
    
    Steps roughly follow:
    ---> Preprocess the raw <where-clause> <limit> inputs
    ---> If <where-clause> is present
    ------> Resolve macros
    ------> Convert <where-clause> to tokenized list
    ------> Convert tokenized list to abstract syntax tree
    ------> Serialize AST to SQL query string representation using post order tree traversal
    ---> Combine the str representations of <where-clause> and <limit> appropriately (or try to)

    """
    raw_where, raw_limit = self._parse_clauses(query)

    ast = None
    if raw_where:
      if macros:
        raw_where = self.resolve_macros(raw_where, macros)
      self.set_tokens(self.tokenize(raw_where))
      ast = self.parse_where()
      # @TODO: Clean up instance variables after parsing?
    
    self.serializer.set_dialect(dialect)
    self.serializer.set_fields(fields)
    return(f'"{self.serializer.serialize_ast(ast, limit=raw_limit)}"')

