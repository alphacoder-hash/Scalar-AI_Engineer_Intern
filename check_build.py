import re, urllib.request
r = urllib.request.urlopen("https://scalar-ai-engineer-intern-5350jl3lr.vercel.app/").read().decode()
m = re.search(r'main\.([a-f0-9]+)\.js', r)
h = m.group(1) if m else "none"
print(f"Bundle hash : {h}")
print(f"New build   : {h != 'ba25189b'}")
