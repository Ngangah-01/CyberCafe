from django.db import models
from django.utils import timezone


# Create your models here.
class Student(models.Model):
    firstname = models.CharField(max_length=20)
    lastname= models.CharField(max_length=20)
    idnumber = models.CharField(max_length=20, unique=True)
    phonenumber = models.IntegerField()

    def __str__(self):
        return f"{self.firstname} {self.lastname} {self.idnumber}"
    
class Payment(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')

    def __str__(self):
        return f"{self.student.firstname} - {self.amount}"
    
class UsageSession(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def duration_in_hours(self):
        if not self.end_time:
            return 0
        duration = self.end_time - self.start_time
        return duration.total_seconds() / 3600  # hours

    def total_amount(self):
        return round(self.duration_in_hours() * 100, 2)

    def __str__(self):
        return f"{self.student.firstname} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"