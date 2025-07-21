import re

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    return ip

def get_lang_from_path(request):
    match = re.match(r'^/([a-z]{2})/', request.path)
    return match.group(1) if match else 'en'