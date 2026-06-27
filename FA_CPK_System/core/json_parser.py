import json
class JsonParser:
    def __init__(self,items): self.items=set(items)
    def parse(self,file):
        with open(file,'r') as f:data=json.load(f)
        for v in data.values():
            if isinstance(v,dict) and 'test' in v: test=v['test']; break
        res=[]
        for t in test:
            if t.get('reference') in self.items:
                try:
                    res.append({'item':t['reference'],'value':float(t['actual']),'lsl':float(t['min']),'usl':float(t['max'])})
                except: pass
        return res