d = open('old_bundle.js', encoding='utf-8', errors='ignore').read()
print('Bundle size:', len(d), 'chars')
print('Has WebSocket:', 'WebSocket' in d)
print('Has railway:', 'railway' in d)
print('Has localhost:', 'localhost' in d)
import re
urls = re.findall(r'https?://[^\s"\'\\<>]+', d)
for u in sorted(set(urls))[:15]:
    print('URL:', u)
