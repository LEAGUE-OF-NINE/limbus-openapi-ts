import re
import subprocess
import shutil
import sys

# File Paths
OAPI_SRC_FILE_PATH = "./limbus-openapi/limbus.yaml"
OAPI_GEN_FILE_NAME = "oapi-gen.ts"
PACKET_TYPES_FILE = "packet-types.ts"
FORMAT_TYPES_FILE = "format-types.ts"
ENDPOINT_FILE = "endpoint.ts"

# Command to run OpenAPI TypeScript generator
BUN_COMMAND = [
    "bun", "openapi-typescript", OAPI_SRC_FILE_PATH,
    "-o", OAPI_GEN_FILE_NAME,
    "--alphabetize", "true",
    "--root-types", "true",
    "--root-types-no-schema-prefix", "true",
    "--make-paths-enum", "true",
]

# Check if Bun is installed
if not shutil.which("bun"):
    print("Error: 'bun' not found. Install it from https://bun.sh/", file=sys.stderr)
    sys.exit(1)

# Run OpenAPI TypeScript generation
try:
    print(f"Running: {' '.join(BUN_COMMAND)}")
    subprocess.run(BUN_COMMAND, check=True)
    print(f"Generated: {OAPI_GEN_FILE_NAME}")
except subprocess.CalledProcessError:
    print("Error: Failed to run bun command. Try installing openapi-typescript first: 'bun i -D openapi-typescript typescript'", file=sys.stderr)
    sys.exit(1)

# Convert a string to PascalCase
def to_pascal_case(text):
    return ''.join(word.capitalize() for word in text.split('/'))

# Read generated TypeScript content
with open(OAPI_GEN_FILE_NAME, "r", encoding="utf-8") as file:
    ts_content = file.read()

# Modify specific API names
ts_content = re.sub(r'(\s+)(PostApi|PostLogin|PostIap|PostLog)(?=.*= "/)',  
                    lambda m: f"{m.group(1)}{m.group(2)[4:]}",  
                    ts_content)
ts_content = ts_content.replace("ApiPaths", "Endpoint")
ts_content = re.sub(r'^\s*export type (ResponseResponse|ResponseResult|RequestBodyRequest|RequestParam).*$\n?', '', ts_content, flags=re.MULTILINE)

# --- Generating format-types.ts ---
format_match = re.search(r"pathItems: never;\n}([\s\S]+?)export type \$defs = Record<string, never>;", ts_content)
if format_match:
    with open(FORMAT_TYPES_FILE, "w", encoding="utf-8") as format_file:
        format_file.write(f'import type {{ components }} from "./{OAPI_GEN_FILE_NAME}";\n' + format_match.group(1).strip() + "\n")
    print(f"Generated: {FORMAT_TYPES_FILE}")
    ts_content = ts_content.replace(format_match.group(0), "pathItems: never;\n}\nexport type $defs = Record<string, never>;")

# --- Generating endpoint.ts ---
endpoint_match = re.search(r"export enum Endpoint \{[\s\S]+?\}", ts_content)
if endpoint_match:
    with open(ENDPOINT_FILE, "w", encoding="utf-8") as endpoint_file:
        endpoint_file.write(endpoint_match.group(0) + "\n")
    print(f"Generated: {ENDPOINT_FILE}")
    ts_content = ts_content.replace(endpoint_match.group(0) + "\n", "")

# Write cleaned-up TypeScript file
with open(OAPI_GEN_FILE_NAME, "w", encoding="utf-8") as file:
    file.write(ts_content)

# --- Generating packet-types.ts ---
caps = re.findall(r'^\s*"([^"]+)": \{', ts_content, re.MULTILINE)
output_lines, skipped = set(), set()

for c in caps:
    if not c.startswith("/"):
        skipped.add(c)
        continue
    path_parts = c.strip("/").split("/")
    if len(path_parts) < 2:
        skipped.add(c)
        continue
    type_name = to_pascal_case(path_parts[0]) + path_parts[1]
    output_lines.add(
        f'export type {type_name}Rsp = paths["{c}"]["post"]["responses"][200]["content"]["application/json"];\n' +
        f'export type {type_name}Req = paths["{c}"]["post"]["requestBody"]["content"]["application/json"];'
    )

# Write packet-types.ts
with open(PACKET_TYPES_FILE, "w", encoding="utf-8") as output_file:
    output_file.write(f'import type {{ paths }} from "./{OAPI_GEN_FILE_NAME}";\n' + "\n".join(sorted(output_lines)) + "\n")

print(f"Generated: {PACKET_TYPES_FILE}")
print(f"Skipped packet-type: {skipped}")
