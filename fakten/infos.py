import json,sys
H="54549dfb9b2c8d510ea84c88e4bcd1c741243f29"
p=json.load(open("plan.json")); a,b=int(sys.argv[1]),int(sys.argv[2])
for i,x in enumerate(p[a:b],a):
    info=dict(autoPublish=True,draft=False,media=[f"https://raw.githubusercontent.com/lgisler0/Motojumpervideos/{H}/fakten/videos/fakten_{x['key']}.mp4"],providers=[{"network":"youtube"}],publicationDate={"dateTime":x["wann"],"timezone":"Europe/Zurich"},text=x["text"],youtubeData=dict(title=x["titel"],type="short",privacy="public",tags=x["tags"],category="SCIENCE_TECHNOLOGY",madeForKids=False,isAiGeneratedContent=False))
    print(i,x["wann"]+"+01:00"); print(json.dumps(info,ensure_ascii=False))
