import json
import os
from ds6_util import *


def create_blank_tpp(project_name):
    tpp_object = { 
        'columns': [ { 'readOnly': True, 'wordWrap': True }, { 'readOnly': False, 'wordWrap': True } ],
        'colHeaders': [ "Original", "Translation" ],
        'project': { 'gameTitle': project_name, 'files': {} } 
    }
    
    return tpp_object

def get_file_object(tpp_object, file_name, format):
    normalized_name = file_name.replace(os.sep, "/")

    if normalized_name not in tpp_object['project']['files']:
        tpp_object['project']['files'][normalized_name] = { 'data': [], 'context': [], 'parameters': [], 'indexIds': {}, 'originalFormat': format }

    if 'selectedId' not in tpp_object['project']:
        tpp_object['project']['selectedId'] = normalized_name
    return tpp_object['project']['files'][normalized_name]

def add_translation(file_object, context, original, translation):
    if original not in file_object['indexIds']:
        file_object['indexIds'][original] = len(file_object['indexIds'])
        file_object['data'].append( [ "" ] )
        file_object['context'].append( [ ] )
        file_object['parameters'].append( [ ] )
    text_index = file_object['indexIds'][original]
    
    file_object['data'][text_index][0] = original
    if context not in file_object['context'][text_index]:
        file_object['context'][text_index].append(context)

    if len(file_object['data'][text_index]) == 1:
        file_object['data'][text_index].append(translation)
    else:
        if file_object['data'][text_index][1] != translation:
            file_object['parameters'][text_index].append( { 'contextStr': context, 'translation': translation } )

if __name__ == '__main__':
    
    if os.path.exists("ds6.trans"):
        tpp_object = json.load(open("ds6.trans", "r"))
    else:
        tpp_object = create_blank_tpp("Dragon Slayer: The Legend of Heroes")

    for root, _, files in os.walk("csv"):
        for filename in files:
            if filename.endswith('.csv'):
                filepath = os.path.join(root, filename)

                file_object = get_file_object(tpp_object, filepath, "DS6 CSV")
                csv_translations = load_translations_csv(filepath)
                notes = load_notes_csv(filepath)

                file_object['indexIds'] = { }
                file_object['data'] = []
                file_object['context'] = []
                file_object['parameters'] = []

                if notes is not None:
                    file_object['note'] = notes

                for context, info in csv_translations.items():
                    # TPP always uses Windows line endings.
                    add_translation(file_object, context, info['original'].replace(os.linesep, "\r\n"), 
                        None if 'translation' not in info else info['translation'].replace(os.linesep, "\r\n"))

    json.dump(tpp_object, open('ds6.trans', 'w+', encoding='utf8'), ensure_ascii=False)
