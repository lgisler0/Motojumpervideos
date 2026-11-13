"""Erstellt plan.json: Reihenfolge (Themen gemischt) und Sendezeiten, 6 pro Tag."""
import json, datetime, itertools
import fakten_studio as fs, fakten_daten as d
nach = {}
for e in d.DATEN:
    nach.setdefault(e[2], []).append(e[0])
reihen = sorted(nach.values(), key=len, reverse=True)
folge = [k for gruppe in itertools.zip_longest(*reihen) for k in gruppe if k]
tag, zeiten, plan = datetime.date(2026, 11, 15), ["12:00", "14:00", "16:00", "18:00", "20:00", "22:00"], []
for i, k in enumerate(folge):
    v = fs.VIDEOS[k]; dt = tag + datetime.timedelta(days=i // 6)
    plan.append(dict(key=k, wann=f"{dt}T{zeiten[i % 6]}:00", titel=v["titel"],
                     text=f"{v['text']}\n\n⏱️ Big questions, answered in 30 seconds. Follow for more! 🚀\n\n#shorts {v['hashtags']} #sciencefacts #didyouknow #facts #science", tags=v["tags"]))
json.dump(plan, open("plan.json", "w"), ensure_ascii=False, indent=1)
print(len(plan), plan[0]["wann"], plan[-1]["wann"], max(len(p["titel"]) for p in plan))
print([p["key"] for p in plan[:12]])
