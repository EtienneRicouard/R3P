from django.http import JsonResponse


def index(request):
    data = {
        'jobId': 'Toto',
    }
    return JsonResponse(data)