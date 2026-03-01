"""Tool JSON schemas for the Anthropic API tool-use interface (AGNT-03).

``AGENT_TOOLS`` is the list passed to ``messages.create(tools=AGENT_TOOLS)``.
Each entry follows the Anthropic ``ToolParam`` structure:
- ``name``: tool identifier
- ``description``: natural-language description for the model
- ``input_schema``: JSON Schema object (type="object") describing the tool's parameters

The 9 tools cover the full build-agent surface: file I/O, shell, search, browser
capture, narration (AGNT-04), and documentation generation (AGNT-05).
Phase 42 wires the sandbox tools to E2B; Phase 44 adds narrate() and document()
as native tool calls replacing NarrationService and DocGenerationService.
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
    {
        "name": "narrate",
        "description": (
            "Narrate a significant action in first-person co-founder voice. "
            "Call this when you start or complete a major step — authentication setup, "
            "database schema design, API routing, feature completion, etc. "
            "Include WHAT you are doing AND WHY, referencing the founder's brief when relevant. "
            "Skip minor actions like individual file writes or grep calls. "
            "Example: 'I\\'m setting up auth with Clerk because your brief specified enterprise-grade security.' "
            "Optionally provide phase_name to signal a GSD phase transition (e.g. 'Authentication Setup')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "First-person narration of the significant action being taken.",
                },
                "phase_name": {
                    "type": "string",
                    "description": (
                        "Optional GSD phase name to signal a phase transition. "
                        "When provided, emits gsd.phase.started event and tracks phase progress. "
                        "Example: 'Authentication Setup', 'Database Schema', 'API Routes'."
                    ),
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "document",
        "description": (
            "Write a section of end-user documentation for the product being built. "
            "Call this progressively as you complete major features — document auth after setting it up, "
            "document onboarding after building it. "
            "Sections: 'overview', 'features', 'getting_started', 'faq'. "
            "Write for the product's end users, not the founder. Plain English, no technical jargon, "
            "no file paths, no framework names. Use 'you' and 'your' throughout."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "enum": ["overview", "features", "getting_started", "faq"],
                    "description": "Documentation section to write.",
                },
                "content": {
                    "type": "string",
                    "description": "Markdown content for the section.",
                },
            },
            "required": ["section", "content"],
        },
    },
]
