from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def bulk_home(request):
    return render(request, 'bulk/home.html')
