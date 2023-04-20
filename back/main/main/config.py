from django.http import HttpResponse


def index(request):
    return HttpResponse("No config available so far")