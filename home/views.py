from django.views import generic
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from home.decorators import client_required, owner_required
from django.http import HttpResponse, JsonResponse
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, get_object_or_404
from django.core.serializers import serialize
from django.views.generic import TemplateView, CreateView
from home.forms import *
from home.models import Salon, Services, Owner, Appointments, Products, Comments, SalonSubscription, Comments
from home.models import Client, Staff
from visits.models import Visit


def index(request):
    salons = Salon.objects.order_by('-rating').all()
    page = request.GET.get('page', 1)
    paginator = Paginator(salons, 16)
    try:
        salons = paginator.page(page)
    except PageNotAnInteger:
        salons = paginator.page(1)
    except EmptyPage:
        salons = paginator.page(paginator.num_pages)
    return render(request, 'home/index.html', {"salons": salons})


def signup_steps(request):

    if request.method == "POST":
        logged_in_user = request.user

        owner = Owner.objects.get(user__username=logged_in_user)

        # Processing form data
        if request.POST['input_data']:

            input_data = json.loads(request.POST['input_data'])[0]

            # Update owner details
            if 'owner_name' in input_data:
                name = input_data['owner_name']
                email = input_data['email']
                phone = input_data['phone']
                location = input_data['location']
                gender = input_data['gender']

                Owner.objects.filter(user=logged_in_user).update(
                    ownerName=name,
                    email=email,
                    phone=phone,
                    location=location,
                    gender=gender)

                results = {
                    'message_type': 'success',
                    'results': 'Account details successfully updated'
                }
                return JsonResponse(results)

            # Create new salon
            elif 'salon_name' in input_data:
                name = input_data['salon_name']
                description = input_data['description']
                paybill = input_data['paybill']
                town = input_data['town']

                if Salon.objects.filter(name=name).count() > 0:
                    results = {
                        'message_type':
                        'error',
                        'results':
                        'A salon with this name exists. Please choose another name'
                    }
                    return JsonResponse(results)

                else:
                    salon = Salon(name=name,
                                  description=description,
                                  owner=owner,
                                  paybill=paybill,
                                  town=town)
                    salon.save()

                    results = {
                        'message_type': 'success',
                        'results': 'Salon added successfully'
                    }
                    return JsonResponse(results)

            elif 'salon_name' in input_data:
                package = input_data['package']
                amount = input_data['amount']
                payment_method = input_data['payment_method']

                salon = Salon.objects.get(owner=owner)
                subscription = SalonSubscription(salon=salon,
                                                 package=package,
                                                 amount=amount,
                                                 payment_method=payment_method,
                                                 who_payed=owner)
                subscription.save()

                results = {
                    'message_type': 'success',
                    'results': 'Payment completed'
                }
                return JsonResponse(results)

        # Forms
        owner_details = OwnerAddInfoForm(request.POST)
        if owner_details.is_valid():
            salonadd = owner_details.save(commit=False)
            salonadd.save()
            return redirect('add_salon')

        add_salon = addSalonForm(request.POST)
        if add_salon.is_valid():
            salonadd = add_salon.save(commit=False)
            salonadd.save()
            return redirect('add_salon')

        salon_subsription = SalonSubscriptionForm(request.POST)
        if salon_subsription.is_valid():
            salonadd = salon_subsription.save(commit=False)
            salonadd.save()
            return redirect('add_salon')

    else:
        owner_details = OwnerAddInfoForm()
        add_salon = addSalonForm
        salon_subsription = SalonSubscriptionForm

    context = {
        'owner_details': owner_details,
        'add_salon': add_salon,
        'salon_subsription': salon_subsription
    }
    return render(request, 'sign-up-steps.html', context)


def comingsoon(request):

    if request.method == "POST":
        temuser_form = TempUserForm(request.POST)
        if temuser_form.is_valid():

            temuser = temuser_form.save(commit=False)

            temuser.save()
            messages.success(request, 'We successfully received your details!')

            return redirect('comingsoon')

    temuser_form = TempUserForm()
    return render(request, 'comingsoon/index-design-2.html',
                  {'temuserf_form': temuser_form})


def client_profile_for_salons(request, pk):
    client = get_object_or_404(Client, pk=pk)
    bookings = (Appointments.objects.filter(client=client.pk)).count()
    return render(request, 'clients/about.html', {
        'client': client,
        'bookings': bookings
    })


def crs(request):
    people = tempuser.objects.all()
    return render(request, "comingsoon/check.html", {'people': people})


def faqs(request):
    return render(request, "faqs/index.html")


def about(request):
    return render(request, "about/index.html")


"""
Takes date and returns a string of the day of the week
"""


def day_of_week(date):
    return date.strftime('%A')[:3].lower()


"""
Takes date and returns a string of the month of the year
"""


def month_of_year(date):
    return date.strftime('%B')[:3].lower()


""" Returns string of all previous 12 month names"""


def months_of_year():
    count = 0
    months = []
    while count < 12:
        date = datetime.now() - relativedelta(months=count)
        month = date.strftime('%B')[:3]
        count += 1

        months.append(month)

    return months[::-1]


monthly_chart_datas = []


@login_required
@owner_required
def dashboard(request):
    salon = get_object_or_404(Salon, owner__ownerName=request.user.owner)
    visits = Visit.objects.get_uri_visits_for(request, uri=salon.slug)
    end_date = datetime.date(datetime.now())
    start_date = end_date - timedelta(days=7)
    end_month = datetime.date(datetime.now())
    start_month = end_month - relativedelta(months=12)
    weekly_appointments = Appointments.objects.filter(
        salon=salon,
        created_date__range=(start_date,
                             end_date)).order_by('created_date').all()
    monthly_appointments = Appointments.objects.filter(
        salon=salon,
        created_date__range=(start_month,
                             end_month)).order_by('created_date').all()

    weekly_chart_data = {
        'mon': 0,
        'tue': 0,
        'wed': 0,
        'thu': 0,
        'fri': 0,
        'sat': 0,
        'sun': 0
    }
    monthly_chart_data = {
        'jan': 0,
        'feb': 0,
        'mar': 0,
        'apr': 0,
        'may': 0,
        'jun': 0,
        'jul': 0,
        'aug': 0,
        'sep': 0,
        'oct': 0,
        'nov': 0,
        'dec': 0,
    }
    for appointment in weekly_appointments:
        weekly_chart_data[day_of_week(
            appointment.created_date)] = weekly_appointments.filter(
                created_date=appointment.created_date).count()
    weekly_chart_data = [
        weekly_chart_data['mon'], weekly_chart_data['tue'],
        weekly_chart_data['wed'], weekly_chart_data['thu'],
        weekly_chart_data['fri'], weekly_chart_data['sat'],
        weekly_chart_data['sun']
    ]
    monthly_appointments_data = []
    for appointment in monthly_appointments:
        monthly_chart_data[month_of_year(
            appointment.created_date)] = monthly_appointments.filter(
                created_date=appointment.created_date).count()

        for month in months_of_year():
            monthly_appointments_data.append(monthly_chart_data[month.lower()])

    appointments = Appointments.objects.filter(salon__owner=request.user.owner)
    context = {
        'salon': salon,
        'months_of_year': months_of_year(),
        'weekly_chart_data': weekly_chart_data,
        'monthly_appointments_data': monthly_appointments_data,
        'appointments': appointments
    }
    return render(request, "dashboard/dashboard.html", context)


@login_required
def profile(request, id):
    user_details = Owner.objects.get(ownerId=id)
    salon_details = Salon.objects.get(ownerId=id)
    context = {'user_details': user_details, 'salon_details': salon_details}
    return render(request, "dashboard/profile.html", context)


@login_required
def reviews(request):
    reviews = Comments.objects.all()
    context = {'reviews': reviews}
    return render(request, "dashboard/reviews.html", context)


"""
 Services CRUD
 """


@login_required
def services(request):
    salon = get_object_or_404(Salon, owner__ownerName=request.user.owner)
    services = Services.objects.filter(salon=salon)

    context = {'services': services, 'salon': salon}

    return render(request, "dashboard/services/index.html", context)


@login_required
def service_new(request):
    if request.method == "POST":
        salon = get_object_or_404(Salon, owner=request.user.owner.pk)
        form = ServiceForm(request.POST)
        if form.is_valid():
            form = form.save(commit=False)
            form.salon = salon
            form.save()
            return redirect('services')
    else:
        form = ServiceForm()
    context = {'form': form}

    return render(request, "dashboard/services/new.html", context)


@login_required
def service_edit(request, id):
    service = get_object_or_404(Services, pk=id)
    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            return redirect('services')
    else:
        form = ServiceForm(instance=service)
    context = {'service': service, 'form': form}
    return render(request, "dashboard/services/edit.html", context)


@login_required
def service_delete(request, id):
    service = get_object_or_404(Services, pk=id)
    service.delete()
    return redirect('services')


"""
 Products CRUD
"""


@login_required
def products(request):
    salon = get_object_or_404(Salon, owner__ownerName=request.user.owner)
    products = Products.objects.filter(salon=salon)

    context = {'products': products, 'salon': salon}

    return render(request, "dashboard/products/index.html", context)


@login_required
def product_new(request):
    if request.method == "POST":
        salon = get_object_or_404(Salon, owner=request.user.owner.pk)
        form = ProductForm(request.POST)
        if form.is_valid():
            form = form.save(commit=False)
            form.salon = salon
            form.save()
            return redirect('products')
    else:
        form = ProductForm()
    context = {'form': form}

    return render(request, "dashboard/products/new.html", context)


@login_required
def product_edit(request, id):
    product = get_object_or_404(Products, pk=id)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('products')
    else:
        form = ProductForm(instance=product)
    context = {'product': product, 'form': form}
    return render(request, "dashboard/products/edit.html", context)


@login_required
def product_delete(request, id):
    product = get_object_or_404(Products, pk=id)
    product.delete()
    return redirect('products')


def salon_details(request, name):
    # Page we are listening for unique urls visits
    Visit.objects.add_uri_visit(request, request.META["PATH_INFO"], 'home')
    salon = get_object_or_404(Salon, slug=name)
    services = Services.objects.filter(salon__name=salon.name)
    products = Products.objects.filter(salon__name=salon.name)
    comments = Comments.objects.filter(
        salon__id=salon.id).order_by("-created_date")
    MAPS_API_KEY = settings.MAPS_API_KEY

    average_rating = 0.0
    stars_1 = stars_2 = stars_3 = stars_4 = stars_5 = 0
    ps1 = ps2 = ps3 = ps4 = ps5 = 0

    for comment in comments:
        if comment.stars == '1 Star':
            stars_1 += 1

        if comment.stars == '2 Stars':
            stars_2 += 1

        if comment.stars == '3 Stars':
            stars_3 += 1

        if comment.stars == '4 Stars':
            stars_4 += 1

        if comment.stars == '5 Stars':
            stars_5 += 1

    total_stars = stars_1 + stars_2 + stars_3 + stars_4 + stars_5
    if total_stars > 0:
        ps1 = (stars_1 / total_stars) * 100
        ps2 = (stars_2 / total_stars) * 100
        ps3 = (stars_3 / total_stars) * 100
        ps4 = (stars_4 / total_stars) * 100
        ps5 = (stars_5 / total_stars) * 100
        average_rating = round((stars_1 + (stars_2 * 2) + (stars_3 * 3) +
                                (stars_4 * 4) + (stars_5 * 5)) / total_stars,
                               1)
        salon.rating = average_rating
        salon.save()
    if request.method == "POST":
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():

            comment = comment_form.save(commit=False)
            comment.salon = salon
            comment.author = request.user

            comment.save()
            messages.success(
                request,
                'Review Received Successfully! It will be posted soon. You can edit it on your Profile'
            )
            return redirect('salon_details', name=name)
    comment_form = CommentForm()

    if request.method == "POST":
        form = clientAppointment(request.POST)
        if form.is_valid():
            clientAppointmentAdd = form.save(commit=False)
            clientAppointmentAdd.client = request.user
            clientAppointmentAdd.salon = salon
            clientAppointmentAdd.totalCost = 900
            clientAppointmentAdd.save()
            messages.success(request, 'Appointment Successfuly booked')
            return redirect('salon_details', name=name)
    form = clientAppointment()

    context = {
        'salon': salon,
        'average_rating': average_rating,
        'services': services,
        'products': products,
        'reviews': comments,
        'counter': 0,
        'comment_form': comment_form,
        'total_stars': total_stars,
        'form': form,
        'clientAppointment': clientAppointment,
        'ps1': ps1,
        'ps2': ps2,
        'ps3': ps3,
        'ps4': ps4,
        'ps5': ps5,
        'MAPS_API_KEY': MAPS_API_KEY,
        'stars_1': stars_1,
        'stars_2': stars_2,
        'stars_3': stars_3,
        'stars_4': stars_4,
        'stars_5': stars_5
    }
    return render(request, "home/salon_details.html", context)


@login_required
def customers(request):
    customers = Client.objects.all()

    if request.method == "POST":
        form = addClientForm(request.POST)
        if form.is_valid():
            salonadd = form.save(commit=False)
            salonadd.save()
            return redirect('customers')
    else:
        formclient = addClientForm()

    context = {
        'client': customers,
        'formclient': formclient,
    }

    return render(request, "dashboard/customers.html", context)


@login_required
def staffs(request):
    # Searching for a staff
    if request.GET.get('keyword'):
        keyword = request.GET.get('keyword')
        filtered_data_query = Staff.objects.filter(
            firstname__icontains=keyword)
        filtered_data = serialize('json', filtered_data_query)

        filtered_data = {
            'data': filtered_data,
            'data_length': len(filtered_data_query)
        }
        return JsonResponse(filtered_data)

    staffs = Staff.objects.all()

    if request.method == "POST":
        # Deleting a staff
        if request.POST.get('staff_to_delete_id'):
            staff_to_delete = request.POST.get('staff_to_delete_id')
            if Staff.objects.filter(pk=staff_to_delete).count() > 0:
                Staff.objects.get(pk=staff_to_delete).delete()
                messages.info(request, 'User succefully deleted')
                return redirect('staffs')
            else:
                messages.error(request, 'That user could not be found')
                return redirect('staffs')

        # Order staff alphabetically
        elif request.POST.get('filter'):
            filter = request.POST.get('filter')
            if filter == 'alphabet':
                filtered_data_query = Staff.objects.all().order_by('firstname')
                filtered_data = serialize('json', filtered_data_query)

                filtered_data = {
                    'data': filtered_data,
                    'data_length': len(filtered_data_query)
                }

                return JsonResponse(filtered_data)

            elif filter == 'date_started':
                filtered_data_query = Staff.objects.all().order_by(
                    'date_started')
                filtered_data = serialize('json', filtered_data_query)

                filtered_data = {
                    'data': filtered_data,
                    'data_length': len(filtered_data_query)
                }

                return JsonResponse(filtered_data)

            elif filter == 'salary':
                filtered_data_query = Staff.objects.all().order_by('salary')
                filtered_data = serialize('json', filtered_data_query)

                filtered_data = {
                    'data': filtered_data,
                    'data_length': len(filtered_data_query)
                }

                return JsonResponse(filtered_data)

    context = {'staffs': staffs}

    return render(request, "dashboard/staff/index.html", context)


@login_required
@owner_required
def staff_new(request):
    if request.method == "POST":
        salon = get_object_or_404(Salon, owner=request.user.owner.pk)
        form = StaffForm(request.POST)
        if form.is_valid():
            form = form.save(commit=False)
            form.salon = salon
            form.save()
            return redirect('staffs')
    else:
        form = StaffForm()
    context = {'form': form}
    return render(request, "dashboard/staff/new.html", context)


@login_required
def staff_edit(request, id):
    staff = get_object_or_404(Staff, pk=id)

    if request.method == "POST":
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            return redirect('staffs')
    else:
        form = StaffForm(instance=staff)
    context = {'staff': staff, 'form': form}

    return render(request, "dashboard/staff/edit.html", context)


@login_required
def staff_delete(request, id):
    staff = get_object_or_404(Staff, pk=id)
    staff.delete()
    return redirect('staffs')


@login_required
@owner_required
def staffs_add(request):
    context = {}
    return render(request, "dashboard/staffs_add.html", context)


@login_required
def dashboard_appointments_new(request):
    context = {}
    return render(request, "dashboard/appointments/new.html", context)


@login_required
def preference(request):
    if request.method == "POST":
        salon_id = request.POST.get('salon_id', None)
        salon = get_object_or_404(Salon, id=salon_id)
        user = request.user

        if salon.likes.filter(id=user.id):
            # User has already liked this salon
            # remove this user like
            salon.likes.remove(user)
            message = "dislike"
        else:
            # user likes salon
            salon.likes.add(user)
            message = "like"
        context = {"likes_count": salon.total_likes, "message": message}
    return HttpResponse(json.dumps(context), content_type='application/json')


def clientPayment(request):
    return render(request, "payment.html")


def upload(request):
    context = {}
    if request.method == 'POST':
        uploaded_file = request.FILES['document']
        fs = FileSystemStorage()
        name = fs.save(uploaded_file.name, uploaded_file)
        context['url'] = fs.url(name)
    return render(request, 'upload.html', context)


class SignUpView(TemplateView):
    template_name = 'registration/signup.html'


def appointments(request):
    my_salon = Appointments.objects.filter(salon__owner=request.user.owner)
    salon = get_object_or_404(Salon, owner=request.user.owner.pk)
    services = Services.objects.filter(salon__name=salon.name)
    products = Products.objects.filter(salon__name=salon.name)
    if request.method == "POST":
        form = clientAppointment(request.POST)
        if form.is_valid():
            clientAppointmentAdd = form.save(commit=False)
            clientAppointmentAdd.client = request.user
            clientAppointmentAdd.salon = salon
            clientAppointmentAdd.totalCost = 900
            clientAppointmentAdd.save()
            form.save_m2m()
            messages.success(request, 'Appointment Successfuly booked')
            return redirect('dashboard_appointments')
    form = clientAppointment()
    context = {
        'services': services,
        'products': products,
        'form': form,
        'my_salon': my_salon,
    }

    return render(request, 'dashboard/appointments/index.html', context)


def appointment_accept(request, pk):
    appointment = get_object_or_404(Appointments, pk=pk)
    appointment.is_pending = False
    appointment.is_rejected = False
    appointment.is_complete = False
    appointment.is_accepted = True
    appointment.save()
    return redirect('appointments', pk=pk)


def appointment_complete(request, pk):
    appointment = get_object_or_404(Appointments, pk=pk)
    appointment.status = 'Completed'
    appointment.save()
    return redirect('dashboard_appointments', )


def appointment_reject(request, pk):
    appointment = get_object_or_404(Appointments, pk=pk)
    appointment.is_pending = False
    appointment.is_rejected = True
    appointment.is_complete = False
    appointment.is_accepted = False
    appointment.save()
    return redirect('appointments', pk=pk)
