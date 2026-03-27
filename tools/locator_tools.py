import json
from pathlib import Path
import os



def locator_tools_registration(mcp):

    @mcp.tool()
    def extract_all_locators(
        input_dir: str = "output/raw",
        output_dir: str = "output/locators"
    ) -> str:
        """
        Extracts all locators from raw TSU JSON files, including all linked XParams
        and nested SelfHealingData for each module attribute.
        """

        input_path = Path(input_dir)
        output_path = Path(output_dir)

        if not input_path.exists():
            return "Raw JSON folder not found."

        json_files = list(input_path.glob("*.json"))
        output_path.mkdir(parents=True, exist_ok=True)

        total = 0

        for file in json_files:

            data = json.loads(file.read_text(encoding="utf-8"))
            entities = data.get("Entities", [])

            # Map all entities by Surrogate for easy lookup
            surrogate_map = {e.get("Surrogate"): e for e in entities if e.get("Surrogate")}

            structured_output = []

            # Get all modules
            modules = [e for e in entities if e.get("ObjectClass") == "XModule"]

            for module in modules:
                module_name = module.get("Attributes", {}).get("Name", "UnknownModule")
                attribute_ids = module.get("Assocs", {}).get("Attributes", [])

                for attr_id in attribute_ids:

                    attr_obj = surrogate_map.get(attr_id)
                    if not attr_obj or attr_obj.get("ObjectClass") != "XModuleAttribute":
                        continue

                    field_name = attr_obj.get("Attributes", {}).get("Name", "UnknownField")
                    business_type = attr_obj.get("Attributes", {}).get("BusinessType", "")

                    locators = {}

                    # Loop over all linked XParams via Properties
                    param_ids = attr_obj.get("Assocs", {}).get("Properties", [])
                    for param_id in param_ids:
                        param_obj = surrogate_map.get(param_id)
                        if not param_obj or param_obj.get("ObjectClass") != "XParam":
                            continue

                        name = param_obj.get("Attributes", {}).get("Name")
                        value = param_obj.get("Attributes", {}).get("Value")
                        if name:
                            locators[name] = value

                        # Check if this XParam has ExtendableObject pointing back to this attribute
                        extend_objs = param_obj.get("Assocs", {}).get("ExtendableObject", [])
                        for ext_id in extend_objs:
                            if ext_id == attr_id:
                                # Already added above
                                continue

                    # Add the structured output
                    structured_output.append({
                        "ModuleName": module_name,
                        "FieldSurrogate": attr_id,
                        "FieldName": field_name,
                        "BusinessType": business_type,
                        "Locators": locators
                    })
            # Write to file
            out_file = output_path / f"{file.stem}_locators.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(structured_output, f, indent=2)

            total += len(structured_output)

        return f"Extracted {total} locators → {output_dir}"
