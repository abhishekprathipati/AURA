import traceback
try:
    import app
except Exception as e:
    with open('error_debug.txt', 'w', encoding='utf-8') as f:
        traceback.print_exc(file=f)
