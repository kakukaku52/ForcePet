from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def rest_explorer_home(request):
    return render(request, 'rest_explorer/home.html')
