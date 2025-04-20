import os
import json
import random
from tqdm import tqdm

from augmentation.system_prompts import (
    version1_descriptions1,
    version1_descriptions2,
    version2_descriptions1,
    version4_descriptions1
)

def get_sorted_json_filepaths(input_dir):
    """
    Retrieve and sort all JSON file paths in a directory.
    
    Args:
        input_dir (str): Path to the directory containing JSON files.

    Returns:
        list: Sorted list of absolute file paths to JSON files.
    """
    json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    json_files.sort()
    json_filepaths = [os.path.abspath(os.path.join(input_dir, f)) for f in json_files]
    return json_filepaths

def read_and_merge_json_files(json_filepaths):
    """
    Read and merge multiple JSON files into a single list.

    Args:
        json_filepaths (list): List of JSON file paths.

    Returns:
        list: Merged data from all JSON files.
    """
    merged_data = []
    for filepath in json_filepaths:
        with open(filepath, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                merged_data.extend(data)
            else:
                merged_data.append(data)
    return merged_data

def process_perturbation_data(merged_data, combine_type="version1", ratio=1.0):
    """
    Process and modify perturbation data based on the specified combine type and ratio.

    Args:
        merged_data (list): List of JSON objects containing perturbation data.
        combine_type (str): Type of combination to apply ("version1", "version2", "version3").
        ratio (float): Ratio to split between different processing types.

    Returns:
        list: Processed perturbation data.
    """

    count = 0

    for data in tqdm(merged_data):
        if 'perturbation_text' in data.keys() and 'image' in data.keys():
            # Version1
            if combine_type == "version1":
                selected_description1 = random.choice(version1_descriptions1)
                selected_description2 = random.choice(version1_descriptions2)
                data['conversations'][0]['value'] = data['conversations'][0]['value'].replace('\n<image>', '').replace('<image>\n', '').replace('<image>', '')
                if random.random() < ratio:
                    count += 1
                    data['conversations'][0]['value'] = '<image>\n' + selected_description1 + ' ' + data['perturbation_text'] + ' ' + selected_description2 + ' ' + data['conversations'][0]['value']
                else:
                    data['conversations'][0]['value'] = '<image>\n' + data['conversations'][0]['value']
            
            # Version2
            elif combine_type == "version2":
                selected_description1 = random.choice(version2_descriptions1)
                data['conversations'][0]['value'] = data['conversations'][0]['value'].replace('\n<image>', '').replace('<image>\n', '').replace('<image>', '')
                if random.random() < ratio:
                    count += 1
                    data['conversations'][0]['value'] = '<image>\n' + data['perturbation_text'] + ' ' + selected_description1 + ' ' + data['conversations'][0]['value']
                else:
                    data['conversations'][0]['value'] = '<image>\n' + data['conversations'][0]['value']
            
            # Version3
            elif combine_type == "version3":
                data['conversations'][0]['value'] = data['conversations'][0]['value'].replace('\n<image>', '').replace('<image>\n', '').replace('<image>', '')
                if random.random() < ratio:
                    count += 1
                    data['conversations'][0]['value'] = '<image>\n' + ' ' + data['perturbation_text'] + ' ' + data['conversations'][0]['value']
                else:
                    data['conversations'][0]['value'] = '<image>\n' + data['conversations'][0]['value']
            
            # Version4
            elif combine_type == "version4":
                selected_description1 = random.choice(version4_descriptions1)
                data['conversations'][0]['value'] = data['conversations'][0]['value'].replace('\n<image>', '').replace('<image>\n', '').replace('<image>', '')
                if random.random() < ratio:
                    count += 1
                    data['conversations'][0]['value'] = '<image>\n' + data['perturbation_text'] + ' ' + selected_description1 + ' ' + data['conversations'][0]['value']
                else:
                    data['conversations'][0]['value'] = '<image>\n' + data['conversations'][0]['value']

    print(f"Total processed: {count}")
    return merged_data

def update_and_save_json_data(total_json_path, merged_data, save_json_path):
    """
    Update a main JSON file with merged perturbation data and save the result.

    Args:
        total_json_path (str): Path to the main JSON file.
        merged_data (list): List of merged perturbation data.
        save_json_path (str): Path to save the updated JSON file.
    """
    with open(total_json_path, 'r', encoding='utf-8') as file:
        total_data = json.load(file)

    # Create a dictionary for quick lookup based on 'id'
    merged_data_dict = {item['id']: item for item in merged_data}

    # Replace the corresponding data in total_data
    for item in tqdm(total_data):
        if item['id'] in merged_data_dict:
            item.update(merged_data_dict[item['id']])

    # Save the updated total_data to a new JSON file
    with open(save_json_path, 'w', encoding='utf-8') as file:
        json.dump(total_data, file, ensure_ascii=False, indent=4)

def main():
    """
    Main function to process JSON files with perturbation data.
    """
    json_root = ''
    total_json_path = ''
    save_json_path = ''

    # Step 1: Load and merge JSON files
    json_file_paths = get_sorted_json_filepaths(json_root)
    merged_json_data = read_and_merge_json_files(json_file_paths)

    # Step 2: Process perturbation data
    combine_type = "version1"  # Choose version1, version2, version3, or version3
    ratio = 1.0  # Adjust ratio as needed
    processed_data = process_perturbation_data(merged_json_data, combine_type=combine_type, ratio=ratio)

    # Step 3: Update and save the combined JSON data
    update_and_save_json_data(total_json_path, processed_data, save_json_path)

if __name__ == "__main__":
    main()