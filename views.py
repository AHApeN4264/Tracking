from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from .models import Room, Reservation, Task, UserTask, Comment, TaskRating, UserProfile
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
from django.contrib.auth import login as auth_login, authenticate
from django.urls import reverse
from decimal import Decimal, InvalidOperation
from datetime import date
import datetime
from django.views.decorators.csrf import csrf_exempt
from datetime import date, timedelta, datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.utils.timezone import now
from django.db.models import Avg

# register, register_delete, login, menu, update_task, task_create, delete_room, delete_task,
# tasks_list, all_tasks_views, error_continued, settings_view, user_data, user_profile, edit_profile, 
# task_info, task_info_grade, task_info_comment, delete_comment, wallet, buy_subscription,

User = get_user_model()

def home(request):
    return HttpResponse(request, 'home.html')

def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

@login_required(login_url='/error-continued')
def settings_view(request):
    return render(request, 'settings.html')

def user_profile(request, id):
    user = get_object_or_404(User, id=id)
    tasks = Task.objects.filter(owner=user).exclude(status='inactive')
    userprofile, created = UserProfile.objects.get_or_create(user=user)
    now = timezone.now()
    
    task_status = request.GET.get('task_status', '')
    activity_status = request.GET.get('activity_status', '')

    # Фильтр по активности
    if activity_status == 'active':
        tasks = tasks.filter(deadline__gte=now)
    elif activity_status == 'inactive':
        tasks = tasks.filter(deadline__lt=now)

    # Фильтр по статусу
    if task_status:
        tasks = tasks.filter(status=task_status)

    context = {
        'userprofile': userprofile,
        'tasks': tasks,
        'user': request.user,
        'title': f"Профіль {user.username}",
        'now': now,
    }
    return render(request, 'user-profile.html', context)

@login_required(login_url='/error-continued')
def edit_profile(request):
    user = request.user
    userprofile, created = UserProfile.objects.get_or_create(user=user)
    user_tasks = Task.objects.filter(owner=user)
    now = timezone.now()

    # Автоматическое обновление статуса подписки
    if not user.subscription_end or user.subscription_end < now:
        user.subscription = 'Нема підписки'
        user.subscription_end = None
        user.save()

    if request.method == "POST":
        # Смена цвета текста
        color = request.POST.get("text_color")
        if color:
            userprofile.text_color = color
            userprofile.save()
            messages.success(request, f"Колір тексту змінено на {color}")
            return redirect('edit-profile')

        action = request.POST.get("action")
        
        if action == "save":
            userprofile.description = request.POST.get("description", "")
            
            if "photo" in request.FILES and request.FILES["photo"]:
                userprofile.photo = request.FILES["photo"]
            
            if "background" in request.FILES and request.FILES["background"]:
                userprofile.background = request.FILES["background"]
                userprofile.background_url = None
            
            selected_bg = request.POST.get("selected_background", "")
            if selected_bg:
                userprofile.background = None
                userprofile.background_url = selected_bg

            userprofile.save()
            messages.success(request, "Інформацію профілю оновлено")
            return redirect('user-profile', id=user.id)

        elif action == "reset_photo":
            userprofile.photo = "photos/login.png"
            userprofile.save()
            messages.success(request, "Аватарка скинута до дефолтної")
            return redirect('edit-profile')
        
        elif action == "reset_background":
            userprofile.background = None
            userprofile.background_url = None
            userprofile.save()
            messages.success(request, "Фон скинуто")
            return redirect('edit-profile')

    context = {
        'userprofile': userprofile,
        'user': user,
        'user_tasks': user_tasks,
        'title': f"Редагувати профіль {user.username}",
        'now': now,
    }
    return render(request, 'edit-profile.html', context)

@login_required(login_url='/error-continued')
def user_data(request, id=None):
    user = request.user
    now = timezone.now()

    # Автоматическое обновление статуса подписки
    if not user.subscription_end or user.subscription_end < now:
        user.subscription = 'Нема підписки'
        user.subscription_end = None
        user.save()

    tasks = Task.objects.filter(owner=user)

    total_completed = sum(int(task.answer_count or 0) for task in tasks)
    total_created = sum(int(task.create_count or 0) for task in tasks)

    return render(request, 'user_data.html', {
        'user': user,
        'total_completed': total_completed,
        'total_created': total_created,
    })

def menu(request, id=None):
    if id == 'none' or id is None:
        user = None
    else:
        try:
            user = User.objects.get(id=id)
        except User.DoesNotExist:
            return redirect('menu_none')
    return render(request, 'menu.html', {'user': user})

@login_required(login_url='/error-continued')
def update_task(request, user_id, task_id):
    user = None
    if str(user_id) != 'none':
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            user = None
    if user is None:
        return redirect('error-continued')

    # Отримуємо задачу
    task = get_object_or_404(Task, id=task_id, owner=user)

    if request.method == 'POST':
        task.title = request.POST.get('title')
        task.description = request.POST.get('description')
        task.tasks = request.POST.get('tasks')
        task.priority = request.POST.get('priority')

        # Підписка
        task.subscription = request.POST.get('subscription')

        # Дата/час
        deadline_str = request.POST.get('deadline')
        if deadline_str:
            task.deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')

        # Статуси
        activity_status = request.POST.get('activity_status')
        task_status = request.POST.get('task_status')

        now = datetime.now()

        if activity_status == 'active' and task.deadline < now:
            task.deadline = now
        elif activity_status == 'inactive' and task.deadline >= now:
            task.deadline = now.replace(year=now.year-1)

        task.status = task_status

        # Правильна відповідь
        task.correct_answer = request.POST.get('correct_answer')

        task.save()
        messages.success(request, "Інформацію про завдання оновлено")
        return redirect('tasks-list', id=user_id)

    return render(request, 'update-task.html', {
        'user': user,
        'task': task,
        'now_str': datetime.now().strftime('%Y-%m-%dT%H:%M')
    })

@login_required(login_url='/error-continued')
def tasks_list(request, id):
    user = get_object_or_404(User, id=id)
    tasks = Task.objects.filter(owner=user)
    now = timezone.now()

    # Фильтрация по приоритету
    priority = request.GET.get('priority')
    if priority:
        tasks = tasks.filter(priority=priority)

    # Фильтрация по активности
    activity_status = request.GET.get('activity_status')
    if activity_status == 'active':
        tasks = tasks.filter(deadline__gte=now)
    elif activity_status == 'inactive':
        tasks = tasks.filter(deadline__lt=now)

    # Фильтрация по статусу завдання
    task_status = request.GET.get('task_status')
    if task_status:
        tasks = tasks.filter(status=task_status)

    # Фильтрация по подписке
    subscription = request.GET.get('subscription')
    if subscription:
        tasks = tasks.filter(subscription=subscription)

    return render(request, 'tasks-list.html', {
        'tasks': tasks,
        'title': 'Список завдань',
        'user': user,
        'now': now,
        'activity_status': activity_status,
        'task_status': task_status,
    })

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        password = request.POST.get('password')
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Користувач з ім'ям '{username}' вже існує")
            return redirect('register')
        if User.objects.filter(email=email).exists():
            messages.error(request, f"Користувач з email '{email}' вже існує")
            return redirect('register')
        if User.objects.filter(phone_number=phone_number).exists():
            messages.error(request, f"Користувач з номером телефону '{phone_number}' вже існує")
            return redirect('register')
        User.objects.create(
            username=username,
            phone_number=phone_number,
            email=email,
            password=make_password(password)
        )
        messages.success(request, "Користувача успішно створено")
        return redirect('login')
    return render(request, 'register.html')

def login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        if not username or not phone_number or not email or not password:
            messages.error(request, "Будь ласка, заповніть все.")
            return render(request, 'login.html')
        errors = []
        user_by_username = User.objects.filter(username=username).first()
        if not user_by_username:
            errors.append("Ім'я користувача не знайдено.")
        user_by_phone = User.objects.filter(phone_number=phone_number).first()
        if not user_by_phone:
            errors.append("Номер телефону не знайдено.")
        user_by_email = User.objects.filter(email=email).first()
        if not user_by_email:
            errors.append("Електронну пошту не знайдено.")
        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'login.html')
        try:
            user = User.objects.get(username=username, phone_number=phone_number, email=email)
        except User.DoesNotExist:
            messages.error(request, "Користувача з такими комбінаціями даних не знайдено.")
            return render(request, 'login.html')
        if not check_password(password, user.password):
            messages.error(request, "Невірний пароль.")
            return render(request, 'login.html')
        auth_login(request, user)
        return redirect(reverse('menu', args=[user.id]))
    return render(request, 'login.html')

def register_delete(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = None
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(phone_number=phone_number)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    user = None
        if user:
            if check_password(password, user.password):
                user.delete()
                messages.success(request, "Користувача успішно видалено")
                return redirect('login')
            else:
                messages.error(request, "Невірний пароль")
        else:
            messages.error(request, "Користувач з такими даними не знайдений")

    return render(request, 'register-delete.html')

@login_required(login_url='/error-continued')
def task_create(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.user.id != user.id:
        return redirect('/error-continued')

    now = timezone.now().replace(second=0, microsecond=0)
    now_str = now.strftime('%Y-%m-%dT%H:%M')

    task = Task.objects.filter(owner=user).last()

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        tasks_text = request.POST.get('tasks')
        correct_answer = request.POST.get('correct_answer')
        priority = request.POST.get('priority')
        deadline_str = request.POST.get('deadline')
        activity_status = request.POST.get('activity_status')
        task_status = request.POST.get('task_status')
        subscription = request.POST.get('subscription')
        photo = request.FILES.get('photo')

        try:
            deadline_dt = timezone.make_aware(
                datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M'),
                timezone.get_current_timezone()
            )
        except (ValueError, TypeError):
            messages.error(request, "Невірний формат дати")
            return redirect('task-create', user_id=user.id)

        new_task = Task.objects.create(
            owner=user,
            title=title,
            description=description,
            tasks=tasks_text,
            correct_answer=correct_answer,
            priority=priority,
            deadline=deadline_dt,
            status=task_status,
            subscription=subscription,
            photo=photo,
            first_data=now.date(),
            last_data=now.date(),
            create_count=+1,
        )

        if activity_status == 'active' and new_task.deadline < now:
            new_task.deadline = now
            new_task.save()
        elif activity_status == 'inactive' and new_task.deadline >= now:
            new_task.deadline = now.replace(year=now.year - 1)
            new_task.save()
        
        messages.success(request, "Завдання успішно створено")
        if request.user.username == 'AHAPEN_4264':
            user.role = 'Творець Сайту'
        else:
            user.role = 'Творець Контенту'
        user.save()
        return redirect('menu', id=user.id)

    return render(request, 'task-create.html', {
        'user': user,
        'now_str': now_str,
        'task': task
    })

@csrf_exempt
def delete_taks_list(request, id):
    if request.method == 'POST':
        try:
            task = Task.objects.get(id=id)
            user_id = task.owner.id
            task.delete()
            messages.success(request, f"Завдання з ID {id} видалено")
        except Task.DoesNotExist:
            messages.error(request, f"Завдання з ID {id} не знайдено")
            user_id = request.user.id
        return redirect('tasks-list', id=user_id)
    else:
        return redirect('tasks-list', id=request.user.id)

@csrf_exempt
def delete_task(request, id):
    if request.method == 'POST':
        try:
            task = Task.objects.get(id=id)
            user_id = task.owner.id
            task.delete()
            messages.success(request, f"Завдання з ID {id} видалено")
        except Room.DoesNotExist:
            messages.error(request, f"Завдання з ID {id} не знайдено")
        return redirect('all-tasks-views')
    else:
        return redirect('all-tasks-views')

def search_room(request, id):
    title_query = request.GET.get('title')
    rooms = []

    if title_query:
        all_rooms = Room.objects.filter(title__icontains=title_query)
        for room in all_rooms:
            try:
                Decimal(room.price)
                rooms.append(room)
            except (InvalidOperation, TypeError, ValueError):
                continue

    context = {
        'title': 'Знайти Кімнату',
        'rooms': rooms,
        'user': request.user,
    }
    return render(request, 'search-room.html', context)

@login_required
def delete_comment(request, comment_id):
    if request.method == 'POST':
        comment = get_object_or_404(Comment, id=comment_id)
        task_id = comment.task.id

        if request.user == comment.user or request.user.role == "Творець Сайту":
            comment.delete()
            messages.success(request, "Коментар видалено")
        else:
            messages.error(request, "У вас немає прав на видалення цього коментаря")

        return redirect('task-info', task_id=task_id)

    return redirect('task-info', task_id=comment.task.id)

def task_info(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    user = request.user
    tasks = Task.objects.all()

    user_task = None
    if user.is_authenticated:
        user_task, created = UserTask.objects.get_or_create(user=user, task=task)

    current_time = timezone.now()
    today = current_time.date()

    # рейтинг
    task.is_reserved = task.first_data <= today <= task.last_data if task.first_data and task.last_data else False

    # средний рейтинг
    average_rating = task.ratings.aggregate(avg=Avg('value'))['avg'] or 0

    # Обновляем статус подписки пользователя
    now = timezone.now()
    if user.is_authenticated: 
        if not user.subscription_end or user.subscription_end < now:
            user.subscription = 'Нема підписки'
            user.subscription_end = None
            user.save()
    else:
        user.subscription = 'Нема підписки'

    if request.method == 'POST' and 'user_answer' in request.POST and user_task.status_answer != 'Виконано':
        user_answer = request.POST.get('user_answer', '').strip()
        correct_answer = (task.correct_answer or '').strip()

        user_task.answer_text = user_answer
        if user_answer == correct_answer:
            user_task.status_answer = 'Виконано'
            task.answer_count += 1
            task.save()
            messages.success(request, "✅ Завдання виконано!")
        else:
            user_task.status_answer = 'Не виконано'
            messages.error(request, "❌ Невірна відповідь, спробуйте ще раз.")
        user_task.save()

    # Добавление комментария
    if request.method == 'POST' and 'comment_text' in request.POST:
        comment_text = request.POST.get('comment_text', '').strip()
        if comment_text:
            Comment.objects.create(user=user, task=task, text=comment_text)
            messages.success(request, "Коментар додано!")

    comments = task.comments.all() 

    context = {
        'task': task,
        'user_task': user_task,
        'comments': comments,
        'title': f'Виконання завдання: {task.title}',
        'now': now,
        'average_rating': average_rating,
    }
    return render(request, 'task-info.html', context)

@login_required(login_url='/error-continued')
def task_info_grade(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if request.method == "POST":
        rating_value = request.POST.get("rating")
        if rating_value:
            try:
                rating_value = float(rating_value)
                TaskRating.objects.update_or_create(
                    task=task,
                    user=request.user,
                    defaults={'value': rating_value}
                )
            except ValueError:
                pass

        return redirect('task-info', task_id=task.id)

@login_required(login_url='/error-continued')
def task_info_comment(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == "POST":
        text = request.POST.get("comment")
        if text.strip():
            Comment.objects.create(
                task=task,
                user=request.user,
                text=text.strip()
            )
        return redirect('task-info', task_id=task.id)
    return redirect('task-info', task_id=task.id)

def all_tasks_views(request, id=None):
    if id:
        user = get_object_or_404(User, id=id)
    else:
        user = request.user

    tasks = Task.objects.all()

    title_query = request.GET.get('title', '')
    selected_priority = request.GET.get('priority', '')
    selected_role_priority = request.GET.get('role_priority', '')
    activity_status = request.GET.get('activity_status', '')
    task_status = request.GET.get('task_status', '')
    subscription = request.GET.get('subscription', '')

    # Фильтр по названию
    if title_query:
        tasks = tasks.filter(title__icontains=title_query)

    # Фильтр по приоритету
    if selected_priority:
        tasks = tasks.filter(priority=selected_priority)

    # Фильтр по роли
    if selected_role_priority == "Творець Сайту":
        tasks = tasks.filter(owner__role='Творець Сайту')
    elif selected_role_priority == "Творець Контенту":
        tasks = tasks.filter(owner__role='Творець Контенту')

    # Фильтр по активности
    current_time = timezone.now()
    if activity_status == 'active':
        tasks = tasks.filter(deadline__gte=current_time)
    elif activity_status == 'inactive':
        tasks = tasks.filter(deadline__lt=current_time)

    # Исключаем скрытые задачи
    tasks = tasks.exclude(status='inactive')     

    # Фильтр по статусу
    if task_status:
        tasks = tasks.filter(status=task_status)

    # Фильтр по подписке
    if subscription:
        tasks = tasks.filter(subscription=subscription)

    today = current_time.date()
    for task in tasks:
        task.is_reserved = task.first_data <= today <= task.last_data if task.first_data and task.last_data else False
        task.average_rating = task.ratings.aggregate(avg=Avg('value'))['avg'] or 0

    for task in tasks:
        if user.is_authenticated: 
            user_task = UserTask.objects.filter(user=user, task=task).first()
            if user_task and user_task.status_answer == 'Виконано':
                task.is_completed = True
            else:
                task.is_completed = False
        else:
            task.is_completed = False
    
        # Подписка
        if user.is_authenticated: 
            if task.subscription == 'Потрібна' and user.subscription != 'Підписка':
                task.requires_subscription = True
            else:
                task.requires_subscription = False
        else:
            task.requires_subscription = False

    # Обновляем статус подписки пользователя
    if user.is_authenticated: 
        if not user.subscription_end or user.subscription_end < current_time:
            user.subscription = 'Нема підписки'
            user.subscription_end = None
            user.save()
    else:
        user.subscription = 'Нема підписки'

    context = {
        'tasks': tasks,
        'user': user,
        'now': current_time,
        'selected_priority': selected_priority,
        'selected_role_priority': selected_role_priority,
        'selected_activity_status': activity_status,
        'selected_task_status': task_status,
        'selected_subscription': subscription,
        'title_query': title_query,
    }

    return render(request, 'all-tasks-views.html', context)

def error_continued(request):
    return render(request, 'error-continued.html')

@login_required(login_url='/error-continued')
def wallet(request):
    if request.method == 'POST':
        amount = request.POST.get('amount') or request.POST.get('custom_amount')
        try:
            amount = Decimal(amount)
            if amount > 0:
                request.user.wallet += amount
                request.user.save()
                messages.success(request, f'Баланс успішно поповнено на {amount:.2f} грн.')
            else:
                messages.error(request, 'Сума має бути більшою за 0.')
        except Exception:
            messages.error(request, 'Некоректне значення.')

        return redirect('wallet')

    return render(request, 'wallet.html', {'title': 'Поповнення балансу'})

@login_required(login_url='/error-continued')
def buy_subscription(request):
    user = request.user
    now = timezone.now()

    # Обновляем статус подписки пользователя
    if not user.subscription_end or user.subscription_end < now:
        user.subscription = 'Нема підписки'
        user.subscription_end = None
        user.save()

    subscription_prices = {
        "1 minute": 0,   # бесплатная 1 минута
        "1 hours": 2,    # 1 час = 2 грн
        "1": 20,         # 1 день = 20 грн
        "10": 150,       # 10 дней = 150 грн
        "30": 300        # 30 дней = 300 грн
    }

    if request.method == 'POST':
        amount = request.POST.get('amount', '0')

        if amount not in subscription_prices:
            messages.error(request, "Невірна сума підписки.")
            return redirect('buy_subscription')

        price = subscription_prices[amount]

        if user.wallet < price:
            messages.error(request, "Недостатньо коштів для покупки підписки!")
            return redirect('buy_subscription')

        user.wallet -= price

        if amount == "1 minute":
            delta = timedelta(minutes=1)
            msg_text = "Безкоштовна 1 хвилина додана!"
        elif amount == "1 hours":
            delta = timedelta(hours=1)
            msg_text = "Підписка продовжена на 1 годину!"
        else:
            days = int(amount)
            delta = timedelta(days=days)
            msg_text = f"Підписка продовжена на {days} днів!"

        user.subscription_end = (user.subscription_end or now) + delta
        user.subscription = 'Підписка'
        user.save()

        messages.success(request, msg_text)
        return redirect('buy_subscription')

    return render(request, 'buy-subscription.html', {'title': 'Купівля підписки'})
