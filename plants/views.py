from django.shortcuts import render, redirect
from .models import Planting

def home(request):
    return redirect('plants:current_plantings')

def current_plantings(request):
    plantings = Planting.objects.all().order_by('harvest_date')
    return render(request, 'plants/current_plantings.html', {'plantings': plantings})