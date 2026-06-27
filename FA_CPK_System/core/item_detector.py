
import os, json
class ItemDetector:
    def detect_items(self, folder):
        items=set()
        for f in os.listdir(folder):
            if f.endswith('.json'):
                with open(os.path.join(folder,f),'r') as fp:
                    data=json.load(fp)
                for k,v in data.items():
                    if isinstance(v,dict) and 'test' in v:
                        for t in v['test']:
                            try:
                                float(t.get('actual'))
                                items.add(t.get('reference'))
                            except:
                                pass
        return sorted(items)
