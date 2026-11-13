import json,sys
p=json.load(open("plan.json")); a,b=int(sys.argv[1]),int(sys.argv[2])
for i,x in enumerate(p[a:b],a):
    print(f"{i} {x['wann']} {x['key']} [{x['text'].split(chr(10))[-1].split()[1]}]\n T: {x['titel']}\n X: {x['text'].split(chr(10))[0]}")
