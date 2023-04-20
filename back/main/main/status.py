from django.http import JsonResponse
from random import randrange

def index(request):

    data = {
        'iteration': randrange(100*200),
        'width': 100,
        'height': 200,
        'jobId': 'Toto',
    }
    return JsonResponse(data)