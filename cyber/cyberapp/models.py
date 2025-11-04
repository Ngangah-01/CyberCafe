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
            # For active sessions, calculate duration up to now
            end = timezone.now()
        else:
            end = self.end_time
        duration = end - self.start_time
        # Calculate hours, minutes, and seconds
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def total_amount(self):
        return round(self.duration_in_hours() * 100, 2)

    def __str__(self):
        return f"{self.student.firstname} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"