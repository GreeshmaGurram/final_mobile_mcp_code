import json
from pathlib import Path
import os




def testcase_tools_registration(mcp):

    @mcp.tool()
    def extract_all_testcases(
        input_dir: str = "output/raw",
        output_dir: str = "output/testcases"
    ) -> str:
        """
        Extracts TestCases + Steps + Actions from all raw TSU JSON files.
        """

        input_path = Path(input_dir)
        output_path = Path(output_dir)

        if not input_path.exists():
            return "Raw JSON folder not found."

        json_files = list(input_path.glob("*.json"))
        output_path.mkdir(parents=True, exist_ok=True)

        total_tc = 0

        for file in json_files:

            data = json.loads(file.read_text(encoding="utf-8"))
            entities = data.get("Entities", [])

            id_map = {e["Surrogate"]: e for e in entities if "Surrogate" in e}
            results = []

            for entity in entities:

                if entity.get("ObjectClass") != "TestCase":
                    continue

                tc_name = entity.get("Attributes", {}).get("Name", "UnnamedTestCase")
                step_ids = entity.get("Assocs", {}).get("Items", [])

                steps = []

                for sid in step_ids:

                    step_obj = id_map.get(sid)
                    if not step_obj or step_obj.get("ObjectClass") != "XTestStep":
                        continue

                    step_name = step_obj.get("Attributes", {}).get("Name", "UnnamedStep")

                    value_ids = step_obj.get("Assocs", {}).get("TestStepValues", [])
                    module_ref = step_obj.get("Assocs", {}).get("Module", [])

                    actions = []
                    field_refs = []

                    for vid in value_ids:

                        vobj = id_map.get(vid)
                        if not vobj or vobj.get("ObjectClass") != "XTestStepValue":
                            continue

                        attrs = vobj.get("Attributes", {})

                        actions.append({
                            "Value": attrs.get("Value"),
                            "ActionMode": attrs.get("ActionMode"),
                            "Operator": attrs.get("Operator"),
                            "DataType": attrs.get("DataType"),
                            "Condition": attrs.get("Condition")
                        })

                        field_refs.extend(
                            vobj.get("Assocs", {}).get("ModuleAttribute", [])
                        )

                    steps.append({
                        "StepName": step_name,
                        "Actions": actions,
                        "ModuleRef": module_ref,
                        "FieldRefs": field_refs
                    })

                results.append({
                    "TestCaseName": tc_name,
                    "Steps": steps
                })

            out_file = output_path / f"{file.stem}_testcases.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)

            total_tc += len(results)

        return f"Extracted {total_tc} testcases → {output_dir}"
