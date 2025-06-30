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

- **PYTHON_CALLS** - Method/function call relationships (Note: May have limited data in current analysis)
- **PYTHON_HAS_PARAMETER** - Parameters belonging to methods/functions
- **PYTHON_HAS_METHOD** - Methods belonging to classes
- **PYTHON_IMPORTS** - Import relationships
- **PYTHON_DEFINES_CLASS** - Files defining classes
- **PYTHON_DEFINES_FUNCTION** - Files defining functions

**Note**: Some relationship types like inheritance (`INHERITS_FROM`) are not currently captured by the analyzer.

### Node Properties

Common properties available on nodes:

- `name` - The name of the entity
- `entityId` - Unique identifier
- `filePath` - Full absolute path to the source file
- `startLine` / `endLine` - Line number ranges
- `startColumn` / `endColumn` - Column number ranges
- `language` - Programming language (Python)
- `createdAt` - Analysis timestamp
- `parentId` - Parent entity ID (available on methods, parameters)

## Common Queries

### 1. Find All Methods in a Class

```cypher
MATCH (c:PythonClass {name: "NostrEvent"})-[:PYTHON_HAS_METHOD]->(m:PythonMethod)
RETURN m.name as method_name
ORDER BY m.name
```

### 2. Find All Python Functions (Non-Class Methods)

```cypher
MATCH (f:PythonFunction)
RETURN f.name as function_name, f.filePath as file_path
ORDER BY f.name
```

### 3. Find All Classes in a File

```cypher
MATCH (f:File)-[:PYTHON_DEFINES_CLASS]->(c:PythonClass)
WHERE f.filePath CONTAINS "events.py" AND NOT c.name STARTS WITH "Test"
RETURN c.name as class_name, c.startLine as line_number, f.filePath as file_path
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

### 5. Find Method Call Relationships (Note: Currently Limited Data)

```cypher
// Note: Method call relationships may not be fully populated in current analysis
MATCH (caller:PythonMethod)-[:PYTHON_CALLS]->(called:PythonMethod)
RETURN caller.name as caller_method,
       called.name as called_method,
       caller.filePath as caller_file
LIMIT 20
```

### 6. Find All Imports in the Project

```cypher
MATCH (f:File)-[:PYTHON_IMPORTS]->(m:PythonModule)
WHERE f.filePath CONTAINS "/src/"
RETURN f.filePath as file_name,
       collect(m.name) as imported_modules
ORDER BY f.filePath
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

### 10. Analyze Code Structure by File

```cypher
MATCH (f:File)
WHERE f.filePath CONTAINS "/src/"
OPTIONAL MATCH (f)-[:PYTHON_DEFINES_CLASS]->(c:PythonClass)
OPTIONAL MATCH (f)-[:PYTHON_DEFINES_FUNCTION]->(func:PythonFunction)
WITH f, c, func,
     size([class IN collect(DISTINCT c) WHERE class.name STARTS WITH "Test"]) as test_class_count,
     count(DISTINCT c) as total_class_count
RETURN f.filePath as file_path,
       total_class_count as class_count,
       count(DISTINCT func) as function_count,
       test_class_count
ORDER BY total_class_count DESC, function_count DESC
```

### 11. Find All Classes and Their Methods

```cypher
MATCH (c:PythonClass)-[:PYTHON_HAS_METHOD]->(m:PythonMethod)
WHERE NOT c.name STARTS WITH "Test"
RETURN c.name as class_name,
       c.filePath as file_path,
       collect(m.name) as methods
ORDER BY c.name
```

### 12. Find Files by Module Type

```cypher
// Find all test files
MATCH (f:File)
WHERE f.filePath CONTAINS "test_" OR f.filePath CONTAINS "/test"
RETURN f.filePath as test_files
ORDER BY f.filePath

// Find all source files (non-test)
MATCH (f:File)
WHERE f.filePath CONTAINS "/src/"
  AND NOT (f.filePath CONTAINS "test_" OR f.filePath CONTAINS "/test")
RETURN f.filePath as source_files
ORDER BY f.filePath
```

### 13. Analyze Method Complexity by Parameter Count

```cypher
MATCH (m:PythonMethod)-[:PYTHON_HAS_PARAMETER]->(p:PythonParameter)
WITH m, count(p) as param_count
RETURN param_count,
       count(m) as method_count,
       collect(m.name)[0..5] as sample_methods
ORDER BY param_count DESC
```

### 14. Find Specific Class and All Its Details

```cypher
MATCH (c:PythonClass {name: "NostrEvent"})
OPTIONAL MATCH (c)-[:PYTHON_HAS_METHOD]->(m:PythonMethod)
OPTIONAL MATCH (m)-[:PYTHON_HAS_PARAMETER]->(p:PythonParameter)
RETURN c.name as class_name,
       c.filePath as file_path,
       c.startLine as start_line,
       collect(DISTINCT {
         method: m.name,
         parameters: collect(DISTINCT p.name)
       }) as methods_with_params
```

### 15. Find Import Dependencies Between Files

```cypher
MATCH (f1:File)-[:PYTHON_IMPORTS]->(m:PythonModule)
MATCH (f2:File)
WHERE f2.filePath CONTAINS m.name
  AND f1 <> f2
  AND f1.filePath CONTAINS "/src/"
  AND f2.filePath CONTAINS "/src/"
RETURN f1.filePath as importing_file,
       f2.filePath as imported_file,
       m.name as module_name
ORDER BY importing_file
```

### Explore Project Directory Structure

```cypher
MATCH (f:File)
WHERE f.filePath CONTAINS "/src/nostr_simulator/"
WITH split(split(f.filePath, "/src/nostr_simulator/")[1], "/")[0] as directory
WHERE directory <> "" AND NOT directory ENDS WITH ".py"
RETURN DISTINCT directory as subdirectories
ORDER BY subdirectories
```

## Advanced Analysis Queries

### Code Complexity Analysis

```cypher
// Find methods with many parameters (potential complexity hotspots)
MATCH (m:PythonMethod)-[:PYTHON_HAS_PARAMETER]->(p:PythonParameter)
WITH m, count(p) as param_count
WHERE param_count > 5
RETURN m.name as method_name,
       param_count,
       m.filePath as file_path
ORDER BY param_count DESC
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
WHERE f.filePath CONTAINS "/src/"
OPTIONAL MATCH (f)-[:PYTHON_DEFINES_CLASS]->(c:PythonClass)
OPTIONAL MATCH (f)-[:PYTHON_DEFINES_FUNCTION]->(func:PythonFunction)
WITH f, c, func,
     size([class IN collect(DISTINCT c) WHERE class.name STARTS WITH "Test"]) as test_classes
RETURN f.filePath as file_path,
       count(DISTINCT c) as classes,
       count(DISTINCT func) as functions,
       test_classes
ORDER BY classes DESC, functions DESC
```

## Practical Examples for Nostr Simulator

Based on the current project structure, here are some practical queries specific to the Nostr Simulator codebase:

### Find All Nostr Protocol Classes

```cypher
MATCH (c:PythonClass)
WHERE c.filePath CONTAINS "/protocol/" AND NOT c.name STARTS WITH "Test"
RETURN c.name as class_name, c.filePath as file_path
ORDER BY c.name
```

### Find All Strategy-Related Classes

```cypher
MATCH (c:PythonClass)
WHERE (c.name CONTAINS "Strategy" OR c.name CONTAINS "Spam" OR c.name CONTAINS "AntiSpam")
  AND NOT c.name STARTS WITH "Test"
RETURN c.name as strategy_class, c.filePath as file_path
ORDER BY c.name
```

### Find All Agent Types and Their Methods

```cypher
MATCH (c:PythonClass)-[:PYTHON_HAS_METHOD]->(m:PythonMethod)
WHERE c.filePath CONTAINS "/agents/" AND NOT c.name STARTS WITH "Test"
RETURN c.name as agent_class,
       collect(m.name) as methods
ORDER BY c.name
```

### Find All Simulation Components

```cypher
MATCH (c:PythonClass)
WHERE c.filePath CONTAINS "/simulation/" AND NOT c.name STARTS WITH "Test"
RETURN c.name as component_class,
       c.filePath as file_path,
       c.startLine as line_number
ORDER BY c.filePath, c.startLine
```

### Find Configuration Classes and Their Structure

```cypher
MATCH (c:PythonClass)
WHERE c.name CONTAINS "Config"
OPTIONAL MATCH (c)-[:PYTHON_HAS_METHOD]->(m:PythonMethod)
RETURN c.name as config_class,
       c.filePath as file_path,
       collect(m.name) as methods
ORDER BY c.name
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

To refresh the analysis after code changes, run the code-analyzer-mcp tool:

```bash
# Using the MCP tool directly (as done in this project)
# The tool will automatically analyze the src/ directory and update Neo4j
```

This will update the Neo4j database with the latest code structure.

## Neo4j Browser

Access the Neo4j browser to:

- Visualize graph relationships
- Run queries interactively
- Export results
- Create custom dashboards

## Connection Details

The database connection details are configured in the MCP settings. Refer to your environment configuration for specific connection parameters.

This code graph database provides powerful insights into the Nostr Simulator codebase structure and can help maintain code quality as the project grows.

## Troubleshooting

### APOC Plugin Error

If you encounter the error "There is no procedure with the name `apoc.meta.data` registered", the APOC plugin is not installed in your Neo4j instance. You can work around this by using basic Cypher queries instead:

```cypher
// Instead of CALL apoc.meta.data(), use:
CALL db.labels() YIELD label RETURN label ORDER BY label
CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType
```

### Database Connection Issues

If you cannot connect to the Neo4j database:

1. Ensure Neo4j is running on the expected port (default: 7687)
2. Check the connection credentials in your MCP configuration
3. Verify the database name is correct (default: codegraph)

### Missing Data

If queries return no results:

1. Ensure the code-analyzer-mcp tool has been run on the src/ directory
2. Check that the Neo4j database contains the expected nodes using: `MATCH (n) RETURN count(n)`
3. Verify you're querying the correct database

## Analysis Workflow for Development

Here's a recommended workflow for using the code graph database during development:

### 1. Initial Project Understanding

```cypher
// Get overview of project structure
MATCH (f:File)
WHERE f.filePath CONTAINS "/src/nostr_simulator/"
WITH split(split(f.filePath, "/src/nostr_simulator/")[1], "/")[0] as directory
WHERE directory <> "" AND NOT directory ENDS WITH ".py"
RETURN DISTINCT directory as subdirectories
ORDER BY subdirectories
```

### 2. Explore Module Components

```cypher
// For each subdirectory, find its classes and functions
MATCH (c:PythonClass)
WHERE c.filePath CONTAINS "/protocol/" AND NOT c.name STARTS WITH "Test"
RETURN c.name as class_name, c.filePath as file_path
ORDER BY c.name
```

### 3. Analyze Class Interface

```cypher
// For a specific class, understand its interface
MATCH (c:PythonClass {name: "NostrEvent"})-[:PYTHON_HAS_METHOD]->(m:PythonMethod)
OPTIONAL MATCH (m)-[:PYTHON_HAS_PARAMETER]->(p:PythonParameter)
RETURN m.name as method_name,
       collect(p.name) as parameters
ORDER BY m.name
```

### 4. Check Test Coverage

```cypher
// Find classes that might need tests
MATCH (c:PythonClass)
WHERE NOT c.name STARTS WITH "Test"
  AND NOT c.name STARTS WITH "Mock"
OPTIONAL MATCH (test:PythonClass)
WHERE test.name = "Test" + c.name
WITH c, test
WHERE test IS NULL
RETURN c.name as potentially_untested_class,
       c.filePath as file_path
ORDER BY c.name
```

### 5. Identify Complex Components

```cypher
// Find classes with many methods (complexity indicators)
MATCH (c:PythonClass)-[:PYTHON_HAS_METHOD]->(m:PythonMethod)
WHERE NOT c.name STARTS WITH "Test"
WITH c, count(m) as method_count
WHERE method_count > 10
RETURN c.name as complex_class,
       method_count,
       c.filePath as file_path
ORDER BY method_count DESC
```

This workflow helps maintain code quality and understand the evolving architecture of the Nostr Simulator project.
