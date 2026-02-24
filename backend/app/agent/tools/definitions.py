"""Tool JSON schemas for the Anthropic API tool-use interface (AGNT-03).

``AGENT_TOOLS`` is the list passed to ``messages.create(tools=AGENT_TOOLS)``.
Each entry follows the Anthropic ``ToolParam`` structure:
- ``name``: tool identifier
- ``description``: natural-language description for the model
- ``input_schema``: JSON Schema object (type="object") describing the tool's parameters

The 7 tools cover the full build-agent surface: file I/O, shell, search, and
browser capture. Phase 42 wires these to an E2B sandbox; Phase 41 uses
``InMemoryToolDispatcher`` stubs.
"""

AGENT_TOOLS: list[dict] = [  # type: ignore[type-arg]
    {
        "name": "read_file",
        "description": "Read the contents of a file in the sandbox.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute file path to read.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a file in the sandbox. "
            "Creates parent directories if they do not exist. "
            "Overwrites the file if it already exists."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute file path to write.",
                },
                "content": {
                    "type": "string",
                    "description": "Full file content to write.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Replace a specific string in an existing file with new content. "
            "Replaces the first occurrence of old_string with new_string."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute file path to edit.",
                },
                "old_string": {
                    "type": "string",
                    "description": "Exact string to find and replace.",
                },
                "new_string": {
                    "type": "string",
                    "description": "Replacement string.",
                },
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "bash",
        "description": (
            "Run a shell command in the sandbox and return its stdout and stderr. "
            "Use for build commands, installing packages, running tests, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute.",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "grep",
        "description": (
            "Search for a regex pattern in files within the sandbox. "
            "Returns matching lines with file paths and line numbers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for.",
                },
                "path": {
                    "type": "string",
                    "description": "File or directory path to search within.",
                },
            },
            "required": ["pattern", "path"],
        },
    },
    {
        "name": "glob",
        "description": (
            "List files in the sandbox matching a glob pattern. "
            "Returns an array of matching absolute file paths."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g. '**/*.py', 'src/*.ts').",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "take_screenshot",
        "description": (
            "Capture a screenshot of the current state of the sandbox browser. "
            "Returns the image as a base64-encoded PNG."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
