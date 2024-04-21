import csv
import json
import os
from pickle import NONE

from ds6_util import *

if __name__ == '__main__':
    tpp_object = json.load(open("ds6.trans", 'r', encoding='utf8'))

    for root, _, files in os.walk("csv"):
        for filename in files:
            if filename.endswith('.csv'):
                filepath = os.path.join(root, filename)

                file_object = tpp_object['project']['files'][filepath]
                csv_translations = load_translations_csv(filepath)

                csv_out = csv.writer(open(filepath, 'w', encoding='utf8', newline=''), quoting=csv.QUOTE_ALL)

                if 'note' in file_object:
                    csv_out.writerow([ "*", file_object['note'] ])

                for context, info in csv_translations.items():
                    index = file_object['indexIds'][info['original']]
                    translation = None
                    for candidate_index, candidate_translation in enumerate(file_object['data'][index]):
                        if candidate_index > 0 and candidate_translation is not None:
                            translation = candidate_translation
                    if translation is None:
                        csv_out.writerow([ context, info['original']])
                    else:
                        csv_out.writerow([ context, info['original'], translation ])

                    if 'parameters' in file_object and index < len(file_object['parameters']) and file_object['parameters'][index] is not None:
                        for parameter in file_object['parameters'][index]:
                            if parameter['contextStr'] == context and len(parameter['translation']) > 0:
                                raise Exception(f"Unsupported context-specific translation of text at {context}!")