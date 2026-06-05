d = open('old_bundle.js', encoding='utf-8', errors='ignore').read()

# Find the error message string
idx = d.find('Something went wrong')
if idx >= 0:
    print('ERROR HANDLER CONTEXT:')
    print(repr(d[max(0,idx-300):idx+100]))
else:
    print('Error string not found')
