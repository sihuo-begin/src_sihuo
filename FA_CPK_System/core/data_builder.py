import os
from core.json_parser import JsonParser
class DataBuilder:
    def __init__(self,c): self.parser=JsonParser(c['items'])
    def build_from_folder(self,folder):
        data={}
        for f in os.listdir(folder):
            if f.endswith('.json'):
                for r in self.parser.parse(os.path.join(folder,f)):
                    k=r['item']
                    if k not in data: data[k]={'values':[], 'lsl':r['lsl'], 'usl':r['usl']}
                    data[k]['values'].append(r['value'])
        return data