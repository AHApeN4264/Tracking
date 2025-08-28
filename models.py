from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings

# python manage.py shell

# user = User.objects.get(username="AHAPEN_4264")
# user.role = "Creator Web Site"  
# user.save()

# python manage.py makemigrations
# python manage.py migrate

class User(AbstractUser):
    wallet = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    subscription = models.CharField(
        max_length=20,
        choices=[
            ('Підписка', 'підписка'),
            ('Нема підписки', 'нема підписки'),
        ],
        default='Нема підписки',
    )
    subscription_end = models.DateTimeField(null=True, blank=True)

    role = models.CharField(
        max_length=20,
        choices=[
            ('Користувач', 'користувач'),
            ('Творець Сайту', 'Творець сайту'),
            ('Творець Контенту', 'творець контенту'),
        ],
        default='Користувач',
    )

class UserProfile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='photos/', default='photos/login.png')
    background = models.ImageField(upload_to='backgrounds/', null=True, blank=True)
    background_url = models.CharField(max_length=500, null=True, blank=True)
    description = models.TextField(null=True, blank=True, default='Немає опису')

    class Meta:
        unique_together = (('user',),)

class Task(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    tasks = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to='photos/')
    correct_answer = models.TextField(null=True, blank=True)
    create_count = models.TextField(null=True, blank=True)
    priority = models.CharField(max_length=50, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], default='medium')
    deadline = models.DateTimeField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_tasks'
    )
    subscription = models.CharField(
        max_length=20,
        choices=[
            ('Не потрібна', 'Не потрібна'),
            ('Потрібна', 'Потрібна'),
        ],
        default='Не потрібна',
    )
    STATUS_CHOICES = [
        ('active', 'Активно'),
        ('inactive', 'Неактивно'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    answer_count = models.IntegerField(default=0)
    first_data = models.DateField()
    last_data = models.DateField()

class UserTask(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    status_answer = models.CharField(
        max_length=20,
        choices=[
            ('Виконано', 'Виконано'),
            ('Не виконано', 'Не виконано'),
        ],
        default='Не виконано',
    )
    answer_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'task')

class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.text[:30]}"

class TaskRating(models.Model):
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('task', 'user') 

# class Booking(models.Model):
    # id = models.AutoField(primary_key=True)
    # id_user = models.ForeignKey(User, on_delete=models.CASCADE)
    # id_room = models.ForeignKey('Room', on_delete=models.CASCADE)

class Room(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to='photos/')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    address = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)
    first_data = models.DateField()
    last_data = models.DateField()


class Reservation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    title = models.CharField(max_length=200)
    photo = models.ImageField(upload_to='photos/')
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    start_date = models.DateField()
    end_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.CharField(max_length=255)

class AdminPanel(models.Model):
    confirmation = models.BooleanField(default=False)
    cancel_reservations = models.BooleanField(default=False)
    edit_booking = models.BooleanField(default=False)
    delete_booking = models.BooleanField(default=False)

class Calendar(models.Model):
    free_rooms = models.BooleanField(default=True)
    busy_rooms = models.BooleanField(default=False)
    filter_by_date = models.DateField()

class AddEditRoom(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    add_room = models.BooleanField(default=False)
    edit_room = models.BooleanField(default=False)
    delete_information_room = models.BooleanField(default=False)
    delete_room = models.BooleanField(default=False)
