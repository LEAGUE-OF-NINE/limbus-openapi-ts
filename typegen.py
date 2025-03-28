import re
import subprocess
import shutil

OAPI_SRC_FILE_PATH = "./limbus-openapi/limbus.yaml"
OAPI_GEN_FILE_NAME = "oapi-gen.ts"
OAPI_INTERFACE_IMPORT = f'import type {{ paths }} from "./{OAPI_GEN_FILE_NAME}";\n'
PACKET_OUT_FILE_NAME = "packet-types.ts"
ENDPOINT_REGEX = r'^\s*"([^"]+)": \{'
BUN_COMMAND = ["bun", "openapi-typescript", OAPI_SRC_FILE_PATH, "-o", OAPI_GEN_FILE_NAME]

if not shutil.which("bun"):
    print("bun not found, install from https://bun.sh/", file=sys.stderr)
    sys.exit(1)

try:
    print(f"Running: {BUN_COMMAND}")
    subprocess.run(BUN_COMMAND, check=True)
    print(f"OK! Got output: {OAPI_GEN_FILE_NAME}\nGenerating {PACKET_OUT_FILE_NAME} now.")
except Exception:
    print(f"failed running bun command. try installing openapi-typescript first: `bun i -D openapi-typescript typescript`", file=sys.stderr)
    sys.exit(1)

def to_pascal_case(text):
    return ''.join(word.capitalize() for word in text.split('/'))

with open(OAPI_GEN_FILE_NAME, "r", encoding="utf-8") as file:
    ts_content = file.read()

caps = re.findall(ENDPOINT_REGEX, ts_content, re.MULTILINE)

output_lines = set()
skipped = set()

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

output_lines = sorted(output_lines)

with open(PACKET_OUT_FILE_NAME, "w", encoding="utf-8") as output_file:
    output_file.write(OAPI_INTERFACE_IMPORT + "\n".join(output_lines) + "\n")

print(f"Skipped: {skipped}")
print(f"OK! Generated {PACKET_OUT_FILE_NAME}")
