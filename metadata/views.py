from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def metadata_home(request):
    return render(request, 'metadata/home.html')
