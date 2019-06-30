from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    context = {'message': "Hello, world. This is the home page."}
    
    return render(request, 'index.html', context)
