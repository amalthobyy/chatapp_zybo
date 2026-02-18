from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages as django_messages

from .models import User, Message
from .forms import RegisterForm, LoginForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('user_list')

    form = RegisterForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            django_messages.success(request, 'Account created successfully! Please login.')
            return redirect('login')

    return render(request, 'register.html', {'form': form})



def login_view(request):
    if request.user.is_authenticated:
        return redirect('user_list')

    form = LoginForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            email    = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user     = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                user.is_online = True
                user.save()
                return redirect('user_list')
            else:
                django_messages.error(request, 'Invalid email or password. Please try again.')

    return render(request, 'login.html', {'form': form})



@login_required
def logout_view(request):
    request.user.is_online = False
    request.user.last_seen = timezone.now()
    request.user.save()
    logout(request)
    return redirect('login')



@login_required
def user_list_view(request):
    users = User.objects.exclude(id=request.user.id).filter(is_active=True)

    for user in users:
        user.unread_count = Message.objects.filter(
            sender=user,
            receiver=request.user,
            is_read=False,
            is_deleted=False
        ).count()

    return render(request, 'user_list.html', {'users': users})



@login_required
def chat_view(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    Message.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)

    
    chat_messages = Message.objects.filter(
        sender__in=[request.user, other_user],
        receiver__in=[request.user, other_user],
        is_deleted=False
    ).order_by('timestamp')

    return render(request, 'chat.html', {
        'other_user':    other_user,
        'chat_messages': chat_messages,
    })


@login_required
@require_POST
def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    message.is_deleted = True
    message.save()
    return JsonResponse({'status': 'deleted'})


@login_required
def unread_counts(request):
    from django.http import JsonResponse
    users = User.objects.exclude(id=request.user.id).filter(is_active=True)
    counts = []
    for user in users:
        count = Message.objects.filter(
            sender=user,
            receiver=request.user,
            is_read=False,
            is_deleted=False
        ).count()
        counts.append({'user_id': user.id, 'count': count})
    return JsonResponse({'counts': counts})