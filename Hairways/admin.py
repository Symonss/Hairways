from django.contrib import admin
from .models import Owners, Comments, Services, Appointments, Salons
# Register your models here.
admin.site.register(Owners)
admin.site.register(Comments)
admin.site.register(Services)
admin.site.register(Appointments)
admin.site.register(Salons)
