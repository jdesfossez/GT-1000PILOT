#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def parse_value_range(value_range_str):
    # Extract numbers within parentheses and convert them to a list of integers
    value_range = [int(x) for x in value_range_str.strip("()").split("-")]
    return value_range


def process_data(lines):
    result = {}
    current_name = None
    current_value_range = None
    offset = 0

    for line in lines:
        # Remove leading and trailing whitespace
        line = line.strip()

        print(line)

        if current_name and line.startswith("| | |"):
            # EQ range is not written as a CSV list, fix it manually here
            if line == "| | | -20 - 0 - +20 [dB] |":
                line = "| | | -20dB, -19dB, -18dB, -17dB, -16dB, -15dB, -14dB, -13dB, -12dB, -11dB, -10dB, -9dB, -8dB, -7dB, -6dB, -5dB, -4dB, -3dB, -2dB, -1dB, +0dB, +1dB, +2dB, +3dB, +4dB, +5dB, +6dB, +7dB, +8dB, +9dB, +10dB, +11dB, +12dB, +13dB, +14dB, +15dB, +16dB, +17dB, +18dB, +19dB, +20dB |"
            # This line contains a list of options
            options = line.split("|")[3].split(",")
            options = [opt.strip() for opt in options if opt.strip()]

            # Map each option to a corresponding value within the range
            start_value = current_value_range[0] + offset
            for i, option in enumerate(options):
                result[current_name]["values"][option] = start_value + i
                offset += 1
        elif line.startswith("|") and len(line.split("|")) > 3:
            # This line contains the address, ignore part, name, and value range
            parts = line.split("|")
            offset_txt = parts[1].strip()
            offset_bytes = []
            for i in offset_txt.split(" "):
                offset_bytes.append(int(i, 16))

            name_with_range = parts[3].strip()
            name, value_range = name_with_range.rsplit("(", 1)
            name = name.strip()
            value_range = parse_value_range(value_range)

            # Prepare a dictionary for this name
            result[name] = {
                "offset": offset_bytes,
                "value_range": value_range,
                "values": {},
            }
            current_name = name
            current_value_range = value_range
            offset = 0

    return result


def main():
    parser = argparse.ArgumentParser(description="Convert input file to JSON format.")
    parser.add_argument("input_file", type=str, help="Path to the input file")
    parser.add_argument(
        "-o", "--output_file", type=str, help="Path to the output JSON file"
    )

    args = parser.parse_args()

    # Use pathlib to handle file paths
    input_path = Path(args.input_file)

    # Check if input file exists
    if not input_path.is_file():
        print(f"Error: The file '{input_path}' does not exist.")
        return

    # Read the input file
    with input_path.open("r") as file:
        lines = file.readlines()

    # Process the data
    converted_data = process_data(lines)

    # Convert to JSON string
    json_output = json.dumps(converted_data, indent=4)

    # Determine output path
    if args.output_file:
        output_path = Path(args.output_file)
    else:
        output_path = input_path.with_suffix(".json")

    # Write the output to a file
    with output_path.open("w") as output_file:
        output_file.write(json_output)
        print(f"JSON output saved to '{output_path}'")


if __name__ == "__main__":
    main()
