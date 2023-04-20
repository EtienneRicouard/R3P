from django.http import HttpResponse
from PIL import Image

def index(request):
    red = Image.new('RGBA', (200, 100), (255,0,0,255))
    response = HttpResponse(content_type='application/octet-stream')
    response.write(red.tobytes())
    return response