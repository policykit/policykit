import pathlib
import json

SOURCE_DIR = "../example_policies"
OUTPUT_FILE = "source/generated_example_policies.inc"
LONG_TITLE_SEP = "----------------------------------------------------------------------"


def json_to_rst(policy_data):
    print(f"Formatting policy: '{policy_data['name']}'")
    sections = []
    # Format name and description
    sections.append(f"\n{policy_data['name']}")
    sections.append(f"{LONG_TITLE_SEP}\n")
    if policy_data.get("description"):
        sections.append(f"{policy_data['description']}\n")

    # Format action kind (trigger, constitution, etc)
    if policy_data.get("policy_kind"):
        sections.append(f"**Policy Kind:** ``{policy_data['policy_kind']}``\n")
    # Format action types
    if policy_data.get("action_types"):
        action_types = [f"``{a}``" for a in policy_data["action_types"]]
        sections.append(f"**Action Types:** {','.join(action_types)}")

    # Format code blocks
    for step in ["filter", "initialize", "check", "notify", "success", "fail"]:
        if not policy_data.get(step):
            continue

        policy_code_str = policy_data[step].replace("\n", "\n    ")
        policy_code_section = f"""
**{'Pass' if step == 'success' else step.capitalize()}:**

.. code-block:: python

    {policy_code_str}

"""
        # print(policy_code_section)
        sections.append(policy_code_section)

    policy_rst = "\n".join(sections)
    return policy_rst


def main():
    fn = pathlib.Path(__file__).parent / SOURCE_DIR
    json_policy_filepaths = []
    for x in fn.iterdir():
        if x.suffix == ".json":
            json_policy_filepaths.append(x)

    # Load policy data from files
    all_policy_data = []
    for fp in json_policy_filepaths:
        with open(fp) as f:
            data = json.load(f)
            all_policy_data.append(data)

    # Sort policies by name so that we have a deterministic outcome
    all_policy_data.sort(key=lambda x: x["name"], reverse=True)

    # Convert all policy data to rst strings
    all_policy_strings = []
    for data in all_policy_data:
        rst = json_to_rst(data)
        # print(rst)
        all_policy_strings.append(rst)

    # Write to output file
    output = open(OUTPUT_FILE, "w")
    final_rst = "\n".join(all_policy_strings)
    output.write(final_rst)
    output.close()


main()