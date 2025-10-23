from django.shortcuts import render

def doc_admin_view(request):
    return render(request, 'admin.html')

def doc_customer_view(request):
    return render(request, 'customer.html')

def doc_staff_view(request):
    return render(request, 'staff.html')
