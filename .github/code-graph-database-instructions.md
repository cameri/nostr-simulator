# Code Graph Database Instructions

This document provides comprehensive instructions for using the Neo4j code graph database to analyze the Nostr Simulator codebase.

## Overview

The code-analyzer-mcp tool has analyzed the entire codebase and stored it as a graph database in Neo4j. This allows for powerful querying and analysis of code structure, dependencies, and relationships.

## Database Schema

### Node Types

The database contains the following node types:

- **PythonVariable** - Variables defined in the code
- **PythonParameter** - Function/method parameters
- **PythonMethod** - Class methods and instance methods
- **PythonModule** - Python modules (imports)
- **PythonClass** - Class definitions
- **File** - Source code files
- **PythonFunction** - Standalone functions

### Relationship Types

The database uses these relationship types:

- **PYTHON_CALLS** - Method/function call relationships
- **PYTHON_HAS_PARAMETER** - Parameters belonging to methods/functions
- **PYTHON_HAS_METHOD** - Methods belonging to classes
- **PYTHON_IMPORTS** - Import relationships
- **PYTHON_DEFINES_CLASS** - Files defining classes
- **PYTHON_DEFINES_FUNCTION** - Files defining functions

### Node Properties

Common properties available on nodes:

- `name` - The name of the entity
- `entityId` - Unique identifier
- `filePath` - Path to the source file
- `startLine` / `endLine` - Line number ranges
- `startColumn` / `endColumn` - Column number ranges
- `language` - Programming language (Python)
- `createdAt` - Analysis timestamp
- `parentId` - Parent entity ID (for nested entities)

## Common Queries

### 1. Find All Methods in a Class

```cypher
MATCH (c:PythonClass {name: "NostrEvent"})-[:PYTHON_HAS_METHOD]->(m:PythonMethod)
RETURN m.name as method_name
ORDER BY m.name
```

### 2. Find Class Hierarchies

```cypher
MATCH (c:PythonClass)
OPTIONAL MATCH (c)-[:INHERITS_FROM]->(parent:PythonClass)
RETURN c.name as class_name, parent.name as parent_class
```

### 3. Find All Classes in a File

```cypher
MATCH (f:File {name: "events.py"})-[:PYTHON_DEFINES_CLASS]->(c:PythonClass)
RETURN c.name as class_name, c.startLine as line_number
ORDER BY c.startLine
```

### 4. Find Method Parameters

```cypher
MATCH (c:PythonClass {name: "NostrEvent"})-[:PYTHON_HAS_METHOD]->(m:PythonMethod)
OPTIONAL MATCH (m)-[:PYTHON_HAS_PARAMETER]->(p:PythonParameter)
RETURN m.name as method_name,
       collect(p.name) as parameters
ORDER BY m.name
```

### 5. Find What Methods Call Other Methods

```cypher
MATCH (caller:PythonMethod)-[:PYTHON_CALLS]->(called:PythonMethod)
RETURN caller.name as caller_method,
       called.name as called_method
LIMIT 20
```

### 6. Find All Imports in the Project

```cypher
MATCH (f:File)-[:PYTHON_IMPORTS]->(m:PythonModule)
RETURN f.name as file_name,
       collect(m.name) as imported_modules
ORDER BY f.name
```

### 7. Find Complex Methods (Many Parameters)

```cypher
MATCH (m:PythonMethod)-[:PYTHON_HAS_PARAMETER]->(p:PythonParameter)
WITH m, count(p) as param_count
WHERE param_count > 3
RETURN m.name as method_name,
       param_count,
       m.filePath as file_path
ORDER BY param_count DESC
```

### 8. Find Test Classes and Methods

```cypher
MATCH (c:PythonClass)
WHERE c.name STARTS WITH "Test"
OPTIONAL MATCH (c)-[:PYTHON_HAS_METHOD]->(m:PythonMethod)
WHERE m.name STARTS WITH "test_"
RETURN c.name as test_class,
       count(m) as test_method_count
ORDER BY test_method_count DESC
```

### 9. Find Classes Without Tests

```cypher
MATCH (c:PythonClass)
WHERE NOT c.name STARTS WITH "Test"
  AND NOT c.name STARTS WITH "Mock"
OPTIONAL MATCH (test:PythonClass)
WHERE test.name = "Test" + c.name
WITH c, test
WHERE test IS NULL
RETURN c.name as untested_class, c.filePath as file_path
```

### 10. Analyze Code Coverage by File

```cypher
MATCH (f:File)
OPTIONAL MATCH (f)-[:PYTHON_DEFINES_CLASS]->(c:PythonClass)
OPTIONAL MATCH (f)-[:PYTHON_DEFINES_FUNCTION]->(func:PythonFunction)
OPTIONAL MATCH (test:PythonClass)
WHERE test.name STARTS WITH "Test"
  AND (test.name CONTAINS c.name OR c.name CONTAINS test.name)
RETURN f.name as file_name,
       count(DISTINCT c) as class_count,
       count(DISTINCT func) as function_count,
       count(DISTINCT test) as test_class_count
ORDER BY f.name
```

## Advanced Analysis Queries

### Code Complexity Analysis

```cypher
// Find methods with many calls (potential complexity hotspots)
MATCH (m:PythonMethod)-[:PYTHON_CALLS]->()
WITH m, count(*) as call_count
WHERE call_count > 5
RETURN m.name as method_name,
       call_count,
       m.filePath as file_path
ORDER BY call_count DESC
```

### Dependency Analysis

```cypher
// Find modules with many imports (potential coupling issues)
MATCH (m:PythonModule)<-[:PYTHON_IMPORTS]-()
WITH m, count(*) as import_count
WHERE import_count > 3
RETURN m.name as module_name,
       import_count
ORDER BY import_count DESC
```

### Architecture Overview

```cypher
// Get overview of project structure
MATCH (f:File)
OPTIONAL MATCH (f)-[:PYTHON_DEFINES_CLASS]->(c:PythonClass)
OPTIONAL MATCH (f)-[:PYTHON_DEFINES_FUNCTION]->(func:PythonFunction)
RETURN f.name as file_name,
       count(DISTINCT c) as classes,
       count(DISTINCT func) as functions,
       size([class IN collect(DISTINCT c) WHERE class.name STARTS WITH "Test"]) as test_classes
ORDER BY classes DESC, functions DESC
```

## Usage Tips

### 1. **Start with Overview Queries**

Begin with broad queries to understand the overall structure before diving into specifics.

### 2. **Use LIMIT for Large Results**

Add `LIMIT 10` to queries that might return many results during exploration.

### 3. **Combine Filters**

Use `WHERE` clauses to filter results:

```cypher
WHERE NOT c.name STARTS WITH "Test"
WHERE m.name CONTAINS "validate"
WHERE param_count > 2
```

### 4. **Use OPTIONAL MATCH**

Use `OPTIONAL MATCH` when relationships might not exist to avoid excluding nodes.

### 5. **Collect Related Data**

Use `collect()` to group related items:

```cypher
RETURN m.name, collect(p.name) as parameters
```

## Performance Considerations

- **Index Usage**: The database should have indexes on commonly queried properties like `name`
- **Query Optimization**: Start with more specific nodes (smaller sets) and expand outward
- **Result Limiting**: Use `LIMIT` during exploration to avoid overwhelming results

## Query Patterns for LLMs

When using these queries in automated analysis:

### Pattern 1: Architecture Analysis

Start with file and class overview queries to understand project structure before diving into specific components.

### Pattern 2: Dependency Analysis

Use import and call relationship queries to understand component dependencies and potential coupling issues.

### Pattern 3: Quality Analysis

Combine complexity, test coverage, and parameter count queries to identify code quality issues.

### Pattern 4: Change Impact Analysis

Use call relationship queries to understand the potential impact of changes to specific methods or classes.

## Integration with Development Workflow

### 1. **Code Review**

Use queries to identify complex or untested code before reviews.

### 2. **Refactoring**

Find tightly coupled components that might benefit from refactoring.

### 3. **Documentation**

Generate architecture documentation from graph queries.

### 4. **Quality Metrics**

Track code quality metrics over time using consistent queries.

## Updating the Database

To refresh the analysis after code changes, re-run the code-analyzer-mcp tool. This will update the Neo4j database with the latest code structure.

## Neo4j Browser

Access the Neo4j browser to:

- Visualize graph relationships
- Run queries interactively
- Export results
- Create custom dashboards

## Connection Details

The database connection details are configured in the MCP settings. Refer to your environment configuration for specific connection parameters.

This code graph database provides powerful insights into the Nostr Simulator codebase structure and can help maintain code quality as the project grows.
