def categories(request):
    from .models import Category
    categories = Category.objects.all()  # Or any logic to fetch categories
    return {'categories': categories}

def company(request):
    from .models import Company
    company = Company.objects.all()  # Or any logic to fetch categories
    return {'comapny': company}
