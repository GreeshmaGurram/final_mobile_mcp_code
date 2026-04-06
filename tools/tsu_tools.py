import gzip
import json
from pathlib import Path
import os




def tsu_tools_registration(mcp):

    @mcp.tool()
    def extract_all_tsu(input_dir: str = "input", output_dir: str = "output/raw") -> str:
        """
        Extracts ALL TSU files from a directory and saves raw JSON versions.
        """

        input_path = Path(input_dir)
        output_path = Path(output_dir)

        if not input_path.exists():
            return f"Input folder not found → {input_dir}"

        tsu_files = list(input_path.glob("*.tsu"))

        if not tsu_files:
            return "No TSU files found."

        output_path.mkdir(parents=True, exist_ok=True)

        count = 0

        for file in tsu_files:
            try:
                try:
                    with gzip.open(file, "rb") as f:
                        raw = f.read()
                except (OSError, gzip.BadGzipFile):
                    raw = file.read_bytes()

                parsed = json.loads(raw.decode("utf-8"))

                out_file = output_path / f"{file.stem}.json"

                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, indent=2)

                count += 1

            except Exception as e:
                print(f"Failed {file.name}: {e}")

        return f"Converted {count} TSU files → {output_dir}"
