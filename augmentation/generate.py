# coding: utf-8
import argparse
import pdb
import random
import sys

import base64
import tarfile

import requests
import time
import hashlib
import hmac
import zipfile
import json

import cv2
import numpy as np
import os

from multiprocessing import Pool, cpu_count
from tqdm import tqdm

from augmentation.gpt_prompt import PROMPT1, PROMPT2
IMAGE_ROOT = ""

class GPT4V(object):
    def __init__(self):
        self.url = ''
        self.configs = [
            {
                'appid': "",
                'appkey': "",
                'source': "",
            },
        ]

    @staticmethod
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    @staticmethod
    def encode_imagebytes(image_bytes):
        return base64.b64encode(image_bytes).decode('utf-8')

    def calcAuthorization(self, config):
        source = config['source']
        appkey = config['appkey']
        timestamp = int(time.time())
        signStr = "x-timestamp: %s\nx-source: %s" % (timestamp, source)
        sign = hmac.new(appkey.encode('utf-8'), signStr.encode('utf-8'), hashlib.sha256).digest()
        return sign.hex(), timestamp

    def __call__(self, messages):
        config = random.choice(self.configs)
        appid = config['appid']
        appkey = config['appkey']
        source = config['source']
        auth, timestamp = self.calcAuthorization(config)
        headers = {
                    "Content-Type": "application/json",
                    "x-appid": appid,
                    "x-source": source,
                    "x-timestamp": str(timestamp),
                    "x-authorization": auth,
                }
        payload = {
            "model": "gpt-4o",
            "messages": messages,
            "max_tokens": 4096
        }
        response = requests.post(self.url, json=payload, headers=headers)
        response_text = json.loads(response.text)
        return {"response": response_text['response'], "usage":response_text['detail']['usage']}

import json
import os
from multiprocessing import Pool
from tqdm import tqdm
from time import sleep

def retry(func, retries=10, delay=2, *args, **kwargs):
    attempt = 0
    while attempt < retries:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            print(f"An error occurred: {exc}, retrying in {delay} seconds...")
            attempt += 1
            sleep(delay)
    raise Exception(f"The function {func.__name__} still failed after {retries} retries.")

def process_meta_info(ann):
    image_path = os.path.join(IMAGE_ROOT, ann['image'])
    if len(ann["conversations"]) == 2:
        instruction = ann["conversations"][0]['value'].replace('\n<image>', '').replace('<image>\n', '').replace('<image>', '')
    else:
        instruction = ann["conversations"][0]['value'].replace('\n<image>', '').replace('<image>\n', '').replace('<image>', '')
        for i in range(2, len(ann["conversations"]), 2):
            assert ann["conversations"][i]['from'] == 'human', "wrong order"
            instruction = instruction + ' ' + ann["conversations"][i]['value']
    if len(ann["conversations"]) == 2:
        answer = ann["conversations"][1]['value'].replace('\n<image>', '').replace('<image>\n', '').replace('<image>', '')
    else:
        answer = ann["conversations"][1]['value'].replace('\n<image>', '').replace('<image>\n', '').replace('<image>', '')
        for i in range(3, len(ann["conversations"]), 2):
            assert ann["conversations"][i]['from'] == 'gpt', "wrong order"
            answer = answer + ' ' + ann["conversations"][i]['value']
    return instruction, answer, [image_path]

def process_and_generate_output(gpt_and_ann):
    try:
        gpt, ann = gpt_and_ann
        instruction, answer, image_assets = process_meta_info(ann)
        txt_post = PROMPT1 % (instruction, answer)
        image_assets = [gpt.encode_image(v) for v in image_assets]
        messages = []
        messages.append({"role": "system", "content": "You are an expert multimodal model attacker..."})
        content = []
        for v in image_assets:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{v}", "detail": "high"}})
        content.append({"type": "text", "text": txt_post})
        messages.append({"role": "user", "content": content})
        output = gpt(messages)
        time.sleep(2)
        messages.append({"role": "assistant", "content": output['response']})
        content = PROMPT2 % (instruction, answer)
        messages.append({"role": "user", "content": content})
        output = gpt(messages)
        output['response'] = output['response'].replace('(Perturbation): ', '', 1).replace('(Perturbation)', '', 1)
        time.sleep(2)
    except Exception as e:
        print(f"Error: {e}")
        return None
    return output

def save_partial_results(results, output_path):
    with open(output_path, "a") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

def process_json_ann(args):
    gpt, ann = args  # Unpack tuple
    if "perturbation_text" in ann.keys():
        return ann
    output = retry(process_and_generate_output, retries=10, delay=2, gpt_and_ann=(gpt, ann))
    if output:
        ann['perturbation_text'] = output['response']
    return ann

def process_json_file(json_file, gpt):
    with open(json_file, 'r', encoding='utf-8') as file:
        json_data = json.load(file)

    meta_datas = [(gpt, ann) for ann in json_data]
    return meta_datas

def get_sorted_json_filepaths(input_dir):
    json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    json_files.sort()
    json_filepaths = [os.path.abspath(os.path.join(input_dir, f)) for f in json_files]
    return json_filepaths

def main(gpt, json_root, output_root, max_threads=4):
    json_file_lists = get_sorted_json_filepaths(json_root)
    json_file_lists = json_file_lists
    for json_file in json_file_lists:
        meta_datas = process_json_file(json_file, gpt)
        results = []

        with Pool(max_threads) as pool:
            for result in tqdm(pool.imap(process_json_ann, meta_datas), total=len(meta_datas)):
                results.append(result)

        json_name = os.path.basename(json_file)
        json_save_dir = os.path.join(output_root, json_name)

        with open(json_save_dir, 'w', encoding='utf-8') as outfile:
            json.dump(results, outfile, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    gpt = GPT4V()
    json_root = ''
    output_root = ''
    max_threads = 20  
    main(gpt, json_root, output_root, max_threads)
