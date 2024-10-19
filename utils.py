import re
import random

def build_neighbors_map(macro_map):
  """
  Build adjacency map for a macro_id graph
  """
  def match_neighbors(macro_str):
    # Define the regex pattern to match ':macro' followed by a double-quoted string
    pattern = r':macro\s+"([^"]+)"'
    return re.findall(pattern, macro_str)
  return {key: match_neighbors(val) for key, val in macro_map.items()}

def has_cycle(macro_map):
  """
  Detect if the input macro_map contains a cycle

  Conceptually this encodes the macro map into an adjacency list graph representation
  We then DFS the map maintaining node states as unexplored, in_process, and visited
  If we see an in_process node while actively exploring, there's a cycle
  """
  neighbors = build_neighbors_map(macro_map)
  visited = set()
  in_process = set()

  def dfs(macro_id, visited, in_process, unexplored, neighbors):
    in_process.add(macro_id)
    res = False
    for n in neighbors[macro_id]:
      if n in in_process:
        res = True
      elif n not in visited:
        if dfs(n, visited, in_process, unexplored, neighbors):
          res = True
    visited.add(macro_id)
    in_process.remove(macro_id)
    unexplored.remove(macro_id)
    return res

  unexplored = set(neighbors.keys())
  res = False
  while len(unexplored):
    start = random.choice(list(unexplored))
    if dfs(start, visited, in_process, unexplored, neighbors):
      res = True
      break
  return res

def reduce_macros(where_raw: str, macro_map: dict) -> str:
  # Regex pattern to match [:macro "<macro_id>"]
  pattern = r'\[:macro\s+"([^"]+)"\]'
  
  # Function to replace a match with the corresponding value from the dictionary
  def replace_match(match):
      macro_id = match.group(1)  # Extract the macro_id from the match
      return macro_map.get(macro_id, match.group(0))  # Replace with the macro value, or keep original if not found
  
  while ':macro' in where_raw:
    # Use re.sub to substitute all matches with corresponding macro values
    where_raw = re.sub(pattern, replace_match, where_raw)
  return where_raw
